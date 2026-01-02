#ifndef GAUSS_NEWTON_OPTIMIZER_H
#define GAUSS_NEWTON_OPTIMIZER_H

#include <vector>
#include <functional>
#include <memory>
#include <Eigen/Dense>

/**
 * @brief Gauss-Newton优化器
 * 
 * 基于MIND论文中的Gauss-Newton配准框架实现
 * 
 * 理论基础 (论文公式10-11):
 * - 线性近似误差项: f(x') ≈ f(x) + J(x)·u
 * - 求解正规方程: (J^T J) u_gn = -J^T f
 * - 更新参数: q_new = q_old + α·u_gn (α为步长因子)
 * 
 * 关键特性:
 * - 使用Eigen进行高效矩阵运算
 * - 支持Levenberg-Marquardt阻尼以提高鲁棒性
 * - 支持线搜索(Backtracking Line Search)避免过大步长
 * - 与RegularStepGradientDescentOptimizer相同的接口,便于切换
 * 
 * 适用场景:
 * - MIND-SSD度量(二次误差函数)
 * - 刚体变换(6参数)和仿射变换(12参数)
 * - 比梯度下降收敛更快,但每次迭代计算量更大
 */
class GaussNewtonOptimizer
{
public:
    using ParametersType = std::vector<double>;
    using ResidualVectorType = std::vector<double>;
    using JacobianMatrixType = std::vector<std::vector<double>>; // row-major: [sample][param]
    
    // 函数类型定义 - 与RegularStepGradientDescentOptimizer兼容
    using CostFunctionType = std::function<double()>;
    using GradientFunctionType = std::function<void(ParametersType&)>;
    using UpdateParametersType = std::function<void(const ParametersType&)>;
    using GetParametersType = std::function<ParametersType()>;
    using SetParametersType = std::function<void(const ParametersType&)>;
    using ObserverType = std::function<void(unsigned int, double, double)>;
    
    // Gauss-Newton特有的函数类型
    using ResidualFunctionType = std::function<void(ResidualVectorType&)>;
    using JacobianFunctionType = std::function<void(JacobianMatrixType&)>;

    GaussNewtonOptimizer();
    ~GaussNewtonOptimizer();

    // =========== 与RegularStepGradientDescentOptimizer兼容的接口 ===========
    
    // 优化参数设置
    void SetLearningRate(double rate) { m_LearningRate = rate; m_CurrentStepLength = rate; }
    void SetMinimumStepLength(double stepLength) { m_MinimumStepLength = stepLength; }
    void SetNumberOfIterations(unsigned int iterations) { m_NumberOfIterations = iterations; }
    void SetRelaxationFactor(double factor) { m_RelaxationFactor = factor; }
    void SetGradientMagnitudeTolerance(double tolerance) { m_GradientMagnitudeTolerance = tolerance; }
    void SetReturnBestParametersAndValue(bool flag) { m_ReturnBestParameters = flag; }
    void SetScales(const ParametersType& scales) { m_Scales = scales; }
    void SetNumberOfParameters(unsigned int num);
    
    // 代价函数和梯度函数 (用于兼容性,也用于线搜索)
    void SetCostFunction(CostFunctionType costFunc) { m_CostFunction = costFunc; }
    void SetGradientFunction(GradientFunctionType gradFunc) { m_GradientFunction = gradFunc; }
    void SetUpdateParametersFunction(UpdateParametersType updateFunc) { m_UpdateParameters = updateFunc; }
    void SetGetParametersFunction(GetParametersType getFunc) { m_GetParameters = getFunc; }
    void SetSetParametersFunction(SetParametersType setFunc) { m_SetParameters = setFunc; }
    
    // =========== Gauss-Newton特有接口 ===========
    
    // 设置残差函数: 返回所有采样点的残差向量 f
    // f[i] = fixedMIND[i] - movingMIND[i] (每个采样点每个通道一个残差)
    void SetResidualFunction(ResidualFunctionType residualFunc) { m_ResidualFunction = residualFunc; }
    
    // 设置雅可比矩阵函数: 返回J矩阵 (m×n), m=残差数, n=参数数
    // J[i][p] = ∂f[i]/∂q[p] = -∇MIND_moving · ∂T/∂q_p
    void SetJacobianFunction(JacobianFunctionType jacobianFunc) { m_JacobianFunction = jacobianFunc; }
    
    // Levenberg-Marquardt阻尼参数
    void SetDampingFactor(double lambda) { m_DampingFactor = lambda; }
    double GetDampingFactor() const { return m_DampingFactor; }
    void SetUseLevenbergMarquardt(bool use) { m_UseLevenbergMarquardt = use; }
    
    // 线搜索参数
    void SetUseLineSearch(bool use) { m_UseLineSearch = use; }
    void SetLineSearchMaxIterations(unsigned int maxIter) { m_LineSearchMaxIterations = maxIter; }
    void SetLineSearchShrinkFactor(double factor) { m_LineSearchShrinkFactor = factor; }
    
    // =========== 执行优化 ===========
    void StartOptimization();
    
    // =========== 获取结果 ===========
    double GetValue() const { return m_CurrentValue; }
    double GetBestValue() const { return m_BestValue; }
    unsigned int GetCurrentIteration() const { return m_CurrentIteration; }
    double GetLearningRate() const { return m_CurrentStepLength; }
    
    // 停止原因
    enum StopCondition { 
        MAXIMUM_ITERATIONS,    // 达到最大迭代次数
        STEP_TOO_SMALL,        // 步长过小
        GRADIENT_TOO_SMALL,    // 梯度过小
        CONVERGED,             // 收敛
        SINGULAR_MATRIX        // 矩阵奇异,无法求解
    };
    StopCondition GetStopCondition() const { return m_StopCondition; }
    
    // =========== 观察者和调试 ===========
    void SetObserver(ObserverType observer) { m_Observer = observer; }
    void SetObserverIterationInterval(unsigned int interval) { m_ObserverIterationInterval = interval; }
    unsigned int GetObserverIterationInterval() const { return m_ObserverIterationInterval; }
    void SetVerbose(bool verbose) { m_Verbose = verbose; }
    bool GetVerbose() const { return m_Verbose; }
    
    // 最大参数更新限制
    void SetMaxParameterUpdate(const ParametersType& maxUpdate) { m_MaxParameterUpdate = maxUpdate; }
    const ParametersType& GetMaxParameterUpdate() const { return m_MaxParameterUpdate; }

private:
    // =========== 优化参数 ===========
    double m_LearningRate;            // 初始步长
    double m_MinimumStepLength;       // 最小步长
    unsigned int m_NumberOfIterations;
    double m_RelaxationFactor;        // 步长回退因子
    double m_GradientMagnitudeTolerance;
    bool m_ReturnBestParameters;
    unsigned int m_NumberOfParameters;
    ParametersType m_Scales;          // 参数尺度
    ParametersType m_MaxParameterUpdate;
    
    // =========== Gauss-Newton特有参数 ===========
    double m_DampingFactor;           // L-M阻尼因子 λ
    bool m_UseLevenbergMarquardt;     // 是否使用L-M阻尼
    bool m_UseLineSearch;             // 是否使用线搜索
    unsigned int m_LineSearchMaxIterations;
    double m_LineSearchShrinkFactor;  // 线搜索步长缩减因子
    
    // =========== 当前状态 ===========
    double m_CurrentValue;
    double m_BestValue;
    unsigned int m_CurrentIteration;
    double m_CurrentStepLength;
    double m_PreviousValue;
    ParametersType m_PreviousParameters;
    ParametersType m_BestParameters;
    StopCondition m_StopCondition;
    
    // =========== 函数指针 ===========
    CostFunctionType m_CostFunction;
    GradientFunctionType m_GradientFunction;
    UpdateParametersType m_UpdateParameters;
    GetParametersType m_GetParameters;
    SetParametersType m_SetParameters;
    ResidualFunctionType m_ResidualFunction;
    JacobianFunctionType m_JacobianFunction;
    
    // =========== 观察者 ===========
    ObserverType m_Observer;
    unsigned int m_ObserverIterationInterval;
    bool m_Verbose;
    
    // =========== 内部方法 ===========
    
    // 执行一步Gauss-Newton更新
    void AdvanceOneStep();
    
    // 回退到梯度下降(当没有残差/雅可比函数时)
    void AdvanceOneStepGradientDescent();
    
    // 求解正规方程 (J^T J + λI) u = -J^T f
    // 返回是否成功求解
    bool SolveNormalEquations(const Eigen::MatrixXd& JtJ, 
                              const Eigen::VectorXd& Jtf,
                              Eigen::VectorXd& u);
    
    // 线搜索: 找到使代价下降的步长
    double LineSearch(const ParametersType& currentParams,
                      const ParametersType& direction,
                      double initialValue);
    
    // 计算尺度化的更新幅度
    double ComputeScaledUpdateMagnitude(const ParametersType& update);
    
    // 应用参数更新限制
    void ClampUpdate(ParametersType& update);
};

#endif // GAUSS_NEWTON_OPTIMIZER_H
