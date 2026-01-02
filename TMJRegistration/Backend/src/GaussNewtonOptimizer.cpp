#include "GaussNewtonOptimizer.h"
#include <iostream>
#include <iomanip>
#include <cmath>
#include <algorithm>
#include <limits>

// ============================================================================
// 构造函数和析构函数
// ============================================================================

GaussNewtonOptimizer::GaussNewtonOptimizer()
    : m_LearningRate(1.0)
    , m_MinimumStepLength(1e-6)
    , m_NumberOfIterations(100)
    , m_RelaxationFactor(0.5)
    , m_GradientMagnitudeTolerance(1e-8)
    , m_ReturnBestParameters(true)
    , m_NumberOfParameters(6)
    , m_DampingFactor(1e-3)           // L-M初始阻尼
    , m_UseLevenbergMarquardt(true)   // 默认启用L-M阻尼提高鲁棒性
    , m_UseLineSearch(true)           // 默认启用线搜索
    , m_LineSearchMaxIterations(10)
    , m_LineSearchShrinkFactor(0.5)
    , m_CurrentValue(0.0)
    , m_BestValue(std::numeric_limits<double>::max())
    , m_CurrentIteration(0)
    , m_CurrentStepLength(1.0)
    , m_PreviousValue(std::numeric_limits<double>::max())
    , m_StopCondition(MAXIMUM_ITERATIONS)
    , m_ObserverIterationInterval(10)
    , m_Verbose(false)
{
}

GaussNewtonOptimizer::~GaussNewtonOptimizer()
{
}

// ============================================================================
// 参数设置
// ============================================================================

void GaussNewtonOptimizer::SetNumberOfParameters(unsigned int num)
{
    m_NumberOfParameters = num;
    m_Scales.resize(num, 1.0);
    m_MaxParameterUpdate.resize(num, std::numeric_limits<double>::max());
}

// ============================================================================
// 主优化循环
// ============================================================================

void GaussNewtonOptimizer::StartOptimization()
{
    if (!m_CostFunction || !m_GetParameters || !m_SetParameters)
    {
        throw std::runtime_error("[GaussNewton] Cost function and parameter functions must be set");
    }
    
    // 检查是否设置了Gauss-Newton特有的函数
    bool useGaussNewton = (m_ResidualFunction && m_JacobianFunction);
    
    if (!useGaussNewton && !m_GradientFunction)
    {
        throw std::runtime_error("[GaussNewton] Either (ResidualFunction + JacobianFunction) or GradientFunction must be set");
    }
    
    // 初始化
    m_StopCondition = MAXIMUM_ITERATIONS;
    m_CurrentIteration = 0;
    m_CurrentStepLength = m_LearningRate;
    m_BestValue = std::numeric_limits<double>::max();
    
    // 获取初始参数和值
    m_PreviousParameters = m_GetParameters();
    m_CurrentValue = m_CostFunction();
    m_PreviousValue = m_CurrentValue;
    
    if (m_CurrentValue < m_BestValue)
    {
        m_BestValue = m_CurrentValue;
        m_BestParameters = m_PreviousParameters;
    }
    
    if (m_Verbose)
    {
        std::cout << "[GaussNewton] Starting optimization with " << m_NumberOfParameters << " parameters" << std::endl;
        std::cout << "[GaussNewton] Initial cost: " << m_CurrentValue << std::endl;
        std::cout << "[GaussNewton] Use L-M damping: " << (m_UseLevenbergMarquardt ? "Yes" : "No") << std::endl;
        std::cout << "[GaussNewton] Use line search: " << (m_UseLineSearch ? "Yes" : "No") << std::endl;
    }
    
    // 主迭代循环
    for (m_CurrentIteration = 0; m_CurrentIteration < m_NumberOfIterations; ++m_CurrentIteration)
    {
        // 调用观察者
        if (m_Observer)
        {
            bool shouldCall = m_Verbose || 
                             (m_CurrentIteration % m_ObserverIterationInterval == 0);
            if (shouldCall)
            {
                m_Observer(m_CurrentIteration, m_CurrentValue, m_CurrentStepLength);
            }
        }
        
        // 执行一步优化
        if (useGaussNewton)
        {
            AdvanceOneStep();
        }
        else
        {
            // 回退到梯度下降(如果没有设置残差/雅可比函数)
            AdvanceOneStepGradientDescent();
        }
        
        // 检查收敛条件
        if (m_StopCondition == STEP_TOO_SMALL || 
            m_StopCondition == GRADIENT_TOO_SMALL ||
            m_StopCondition == SINGULAR_MATRIX ||
            m_StopCondition == CONVERGED)
        {
            break;
        }
    }
    
    // 如果需要返回最佳参数
    if (m_ReturnBestParameters && !m_BestParameters.empty())
    {
        m_SetParameters(m_BestParameters);
        m_CurrentValue = m_BestValue;
    }
    
    // 最终观察者调用
    if (m_Observer)
    {
        m_Observer(m_CurrentIteration, m_CurrentValue, m_CurrentStepLength);
    }
    
    if (m_Verbose)
    {
        std::cout << "[GaussNewton] Optimization finished. Final cost: " << m_CurrentValue << std::endl;
        std::cout << "[GaussNewton] Stop condition: ";
        switch (m_StopCondition)
        {
            case MAXIMUM_ITERATIONS: std::cout << "Maximum iterations"; break;
            case STEP_TOO_SMALL: std::cout << "Step too small"; break;
            case GRADIENT_TOO_SMALL: std::cout << "Gradient too small"; break;
            case CONVERGED: std::cout << "Converged"; break;
            case SINGULAR_MATRIX: std::cout << "Singular matrix"; break;
        }
        std::cout << std::endl;
    }
}

// ============================================================================
// Gauss-Newton更新步骤
// ============================================================================

void GaussNewtonOptimizer::AdvanceOneStep()
{
    // 保存当前参数
    ParametersType currentParams = m_GetParameters();
    m_PreviousParameters = currentParams;
    m_PreviousValue = m_CurrentValue;
    
    // 1. 获取残差向量 f
    ResidualVectorType residuals;
    m_ResidualFunction(residuals);
    
    if (residuals.empty())
    {
        if (m_Verbose)
        {
            std::cerr << "[GaussNewton] Warning: Empty residual vector" << std::endl;
        }
        m_StopCondition = SINGULAR_MATRIX;
        return;
    }
    
    // 2. 获取雅可比矩阵 J (m×n)
    JacobianMatrixType jacobian;
    m_JacobianFunction(jacobian);
    
    if (jacobian.empty() || jacobian[0].size() != m_NumberOfParameters)
    {
        if (m_Verbose)
        {
            std::cerr << "[GaussNewton] Warning: Invalid Jacobian matrix" << std::endl;
        }
        m_StopCondition = SINGULAR_MATRIX;
        return;
    }
    
    const size_t m = residuals.size();   // 残差数量
    const size_t n = m_NumberOfParameters;  // 参数数量
    
    // 3. 转换为Eigen矩阵
    Eigen::VectorXd f(m);
    for (size_t i = 0; i < m; ++i)
    {
        f(i) = residuals[i];
    }
    
    Eigen::MatrixXd J(m, n);
    for (size_t i = 0; i < m; ++i)
    {
        for (size_t j = 0; j < n; ++j)
        {
            // 应用参数尺度: J_scaled = J / scales
            double scale = (j < m_Scales.size()) ? m_Scales[j] : 1.0;
            J(i, j) = jacobian[i][j] / scale;
        }
    }
    
    // 4. 计算 J^T J 和 J^T f
    Eigen::MatrixXd JtJ = J.transpose() * J;
    Eigen::VectorXd Jtf = J.transpose() * f;
    
    // 5. 求解正规方程 (J^T J + λI) u = -J^T f
    Eigen::VectorXd u(n);
    if (!SolveNormalEquations(JtJ, Jtf, u))
    {
        m_StopCondition = SINGULAR_MATRIX;
        return;
    }
    
    // 6. 反向缩放更新量
    ParametersType update(n);
    for (size_t i = 0; i < n; ++i)
    {
        double scale = (i < m_Scales.size()) ? m_Scales[i] : 1.0;
        update[i] = u(i) / scale;
    }
    
    // 7. 应用更新限制
    ClampUpdate(update);
    
    // 8. 计算更新幅度
    double updateMagnitude = ComputeScaledUpdateMagnitude(update);
    
    // 检查更新是否过小
    if (updateMagnitude < m_MinimumStepLength)
    {
        m_StopCondition = STEP_TOO_SMALL;
        return;
    }
    
    // 9. 线搜索或直接更新
    double stepFactor = 1.0;
    if (m_UseLineSearch)
    {
        stepFactor = LineSearch(currentParams, update, m_CurrentValue);
    }
    
    // 10. 应用更新
    ParametersType newParams(n);
    for (size_t i = 0; i < n; ++i)
    {
        newParams[i] = currentParams[i] - stepFactor * update[i];  // 负号因为 u_gn = -inv(JtJ)*Jtf
    }
    m_SetParameters(newParams);
    
    // 11. 计算新的代价值
    double newValue = m_CostFunction();
    
    // 12. 检查是否改进
    if (newValue < m_CurrentValue)
    {
        // 接受更新
        m_CurrentValue = newValue;
        m_CurrentStepLength = stepFactor;
        
        // 更新最佳值
        if (newValue < m_BestValue)
        {
            m_BestValue = newValue;
            m_BestParameters = newParams;
        }
        
        // L-M: 减小阻尼因子
        if (m_UseLevenbergMarquardt)
        {
            m_DampingFactor = std::max(m_DampingFactor * 0.5, 1e-10);
        }
    }
    else
    {
        // 拒绝更新,回退参数
        m_SetParameters(currentParams);
        m_CurrentValue = m_PreviousValue;
        m_CurrentStepLength *= m_RelaxationFactor;
        
        // L-M: 增大阻尼因子
        if (m_UseLevenbergMarquardt)
        {
            m_DampingFactor = std::min(m_DampingFactor * 2.0, 1e6);
        }
        
        // 如果步长过小,停止
        if (m_CurrentStepLength < m_MinimumStepLength)
        {
            m_StopCondition = STEP_TOO_SMALL;
        }
    }
    
    // 检查收敛
    double relativeImprovement = std::abs(m_PreviousValue - m_CurrentValue) / 
                                 (std::abs(m_PreviousValue) + 1e-10);
    if (relativeImprovement < m_GradientMagnitudeTolerance && m_CurrentValue <= m_PreviousValue)
    {
        m_StopCondition = CONVERGED;
    }
}

// ============================================================================
// 梯度下降回退(当没有残差/雅可比函数时使用)
// ============================================================================

void GaussNewtonOptimizer::AdvanceOneStepGradientDescent()
{
    ParametersType currentParams = m_GetParameters();
    m_PreviousParameters = currentParams;
    m_PreviousValue = m_CurrentValue;
    
    // 计算梯度
    ParametersType gradient(m_NumberOfParameters, 0.0);
    m_GradientFunction(gradient);
    
    // 计算尺度化的梯度幅值
    double gradientMagnitude = 0.0;
    for (size_t i = 0; i < m_NumberOfParameters; ++i)
    {
        double scale = (i < m_Scales.size()) ? m_Scales[i] : 1.0;
        double scaledGrad = gradient[i] / scale;
        gradientMagnitude += scaledGrad * scaledGrad;
    }
    gradientMagnitude = std::sqrt(gradientMagnitude);
    
    if (gradientMagnitude < m_GradientMagnitudeTolerance)
    {
        m_StopCondition = GRADIENT_TOO_SMALL;
        return;
    }
    
    // 归一化梯度并更新参数
    ParametersType newParams(m_NumberOfParameters);
    for (size_t i = 0; i < m_NumberOfParameters; ++i)
    {
        double scale = (i < m_Scales.size()) ? m_Scales[i] : 1.0;
        double direction = gradient[i] / (scale * scale * gradientMagnitude);
        newParams[i] = currentParams[i] - m_CurrentStepLength * direction;
    }
    
    m_SetParameters(newParams);
    double newValue = m_CostFunction();
    
    if (newValue < m_CurrentValue)
    {
        m_CurrentValue = newValue;
        if (newValue < m_BestValue)
        {
            m_BestValue = newValue;
            m_BestParameters = newParams;
        }
    }
    else
    {
        m_SetParameters(currentParams);
        m_CurrentValue = m_PreviousValue;
        m_CurrentStepLength *= m_RelaxationFactor;
        
        if (m_CurrentStepLength < m_MinimumStepLength)
        {
            m_StopCondition = STEP_TOO_SMALL;
        }
    }
}

// ============================================================================
// 求解正规方程
// ============================================================================

bool GaussNewtonOptimizer::SolveNormalEquations(const Eigen::MatrixXd& JtJ, 
                                                  const Eigen::VectorXd& Jtf,
                                                  Eigen::VectorXd& u)
{
    const size_t n = JtJ.rows();
    
    // 构建增广矩阵 (J^T J + λI)
    Eigen::MatrixXd A = JtJ;
    if (m_UseLevenbergMarquardt)
    {
        // Levenberg-Marquardt: 添加对角阻尼
        for (size_t i = 0; i < n; ++i)
        {
            A(i, i) += m_DampingFactor * (JtJ(i, i) + 1e-6);  // 使用对角元素缩放的阻尼
        }
    }
    
    // 使用LDLT分解求解 (比LU更稳定,对称正定矩阵)
    Eigen::LDLT<Eigen::MatrixXd> ldlt(A);
    
    if (ldlt.info() != Eigen::Success)
    {
        if (m_Verbose)
        {
            std::cerr << "[GaussNewton] Warning: LDLT decomposition failed" << std::endl;
        }
        return false;
    }
    
    // 检查正定性
    if (!ldlt.isPositive())
    {
        if (m_Verbose)
        {
            std::cerr << "[GaussNewton] Warning: Matrix not positive definite, adding more damping" << std::endl;
        }
        // 增加阻尼重试
        Eigen::MatrixXd A2 = JtJ;
        double strongDamping = std::max(m_DampingFactor * 10.0, 1e-3);
        for (size_t i = 0; i < n; ++i)
        {
            A2(i, i) += strongDamping;
        }
        Eigen::LDLT<Eigen::MatrixXd> ldlt2(A2);
        if (ldlt2.info() != Eigen::Success || !ldlt2.isPositive())
        {
            return false;
        }
        u = ldlt2.solve(-Jtf);
    }
    else
    {
        u = ldlt.solve(-Jtf);
    }
    
    // 检查解是否有效
    if (!u.allFinite())
    {
        if (m_Verbose)
        {
            std::cerr << "[GaussNewton] Warning: Solution contains NaN/Inf" << std::endl;
        }
        return false;
    }
    
    return true;
}

// ============================================================================
// 线搜索
// ============================================================================

double GaussNewtonOptimizer::LineSearch(const ParametersType& currentParams,
                                         const ParametersType& direction,
                                         double initialValue)
{
    double alpha = 1.0;  // 初始步长因子
    const double c = 1e-4;  // Armijo条件参数
    
    // 计算梯度与方向的内积(用于Armijo条件)
    ParametersType gradient(m_NumberOfParameters, 0.0);
    if (m_GradientFunction)
    {
        m_GradientFunction(gradient);
    }
    
    double dirGrad = 0.0;
    for (size_t i = 0; i < m_NumberOfParameters; ++i)
    {
        dirGrad += gradient[i] * direction[i];
    }
    
    // 如果方向不是下降方向,使用小步长
    if (dirGrad >= 0)
    {
        return 0.1;
    }
    
    // Backtracking线搜索
    for (unsigned int iter = 0; iter < m_LineSearchMaxIterations; ++iter)
    {
        // 尝试新参数
        ParametersType newParams(m_NumberOfParameters);
        for (size_t i = 0; i < m_NumberOfParameters; ++i)
        {
            newParams[i] = currentParams[i] - alpha * direction[i];
        }
        m_SetParameters(newParams);
        
        double newValue = m_CostFunction();
        
        // Armijo条件: f(x + α*d) <= f(x) + c*α*∇f·d
        if (newValue <= initialValue + c * alpha * dirGrad)
        {
            // 恢复原参数(让调用者决定是否接受)
            m_SetParameters(currentParams);
            return alpha;
        }
        
        // 缩减步长
        alpha *= m_LineSearchShrinkFactor;
    }
    
    // 恢复原参数
    m_SetParameters(currentParams);
    return alpha;  // 返回最终步长
}

// ============================================================================
// 辅助函数
// ============================================================================

double GaussNewtonOptimizer::ComputeScaledUpdateMagnitude(const ParametersType& update)
{
    double magnitude = 0.0;
    for (size_t i = 0; i < update.size(); ++i)
    {
        double scale = (i < m_Scales.size()) ? m_Scales[i] : 1.0;
        double scaled = update[i] / scale;
        magnitude += scaled * scaled;
    }
    return std::sqrt(magnitude);
}

void GaussNewtonOptimizer::ClampUpdate(ParametersType& update)
{
    for (size_t i = 0; i < update.size(); ++i)
    {
        if (i < m_MaxParameterUpdate.size())
        {
            double maxUpdate = m_MaxParameterUpdate[i];
            if (std::abs(update[i]) > maxUpdate)
            {
                update[i] = (update[i] > 0) ? maxUpdate : -maxUpdate;
            }
        }
    }
}
