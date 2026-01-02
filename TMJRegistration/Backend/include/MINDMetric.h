#ifndef MIND_METRIC_H
#define MIND_METRIC_H

#include <vector>
#include <memory>
#include <random>
#include <array>
#include <functional>
#include <thread>
#include <mutex>
#include <atomic>
#include "itkImage.h"
#include "itkLinearInterpolateImageFunction.h"
#include "itkTransform.h"
#include "itkImageMaskSpatialObject.h"

/**
 * @brief MIND (Modality Independent Neighbourhood Descriptor) 度量类
 * 
 * 基于论文: Heinrich M.P., et al. "MIND: Modality independent neighbourhood 
 * descriptor for multi-modal deformable registration" (Medical Image Analysis, 2012)
 * 
 * MIND通过计算图像的局部自相似性模式，将多模态配准问题转化为单模态问题(SSD)
 * 
 * 核心算法：
 * 1. 对于每个体素x，计算其与邻域点的差异
 * 2. MIND(x,r) = (1/n) * exp(-D(x,x+r)^2 / V(x))
 *    其中 D(x,x+r) = (I(x) - I(x+r))^2 是局部差异
 *    V(x) 是局部方差估计（用于归一化）
 * 3. 最终度量是两幅图像MIND特征之间的SSD
 * 
 * 特性:
 * - 3D实现，支持6邻域或26邻域
 * - 与现有优化器框架兼容
 * - 支持解析梯度计算（通过有限差分）
 */
class MINDMetric
{
public:
    using ImageType = itk::Image<float, 3>;
    using MaskImageType = itk::Image<unsigned char, 3>;
    using MaskSpatialObjectType = itk::ImageMaskSpatialObject<3>;
    using InterpolatorType = itk::LinearInterpolateImageFunction<ImageType, double>;
    using TransformBaseType = itk::Transform<double, 3, 3>;
    using ParametersType = std::vector<double>;
    
    // MIND特征图类型：每个位置有N个通道（N=邻域大小）
    using MINDFeatureType = itk::Image<float, 4>;  // 4D: x,y,z,channel
    
    // 雅可比矩阵计算回调类型（与MattesMutualInformation兼容）
    using JacobianFunctionType = std::function<void(const ImageType::PointType&, 
                                                     std::vector<std::array<double, 3>>&)>;
    
    // 邻域类型枚举
    enum class NeighborhoodType
    {
        SixConnected,    // 6邻域: ±x, ±y, ±z (faces)
        TwentySixConnected  // 26邻域: full 3x3x3 cube excluding center
    };

    MINDMetric();
    ~MINDMetric();

    void SetVerbose(bool v) { m_Verbose = v; }
    bool GetVerbose() const { return m_Verbose; }

    // 设置固定图像和移动图像
    void SetFixedImage(ImageType::Pointer fixedImage);
    void SetMovingImage(ImageType::Pointer movingImage);
    
    // 设置变换(使用通用变换基类)
    void SetTransform(TransformBaseType::Pointer transform) { m_Transform = transform; }
    
    // 设置雅可比矩阵计算函数(由外部提供)
    void SetJacobianFunction(JacobianFunctionType func) { m_JacobianFunction = func; }
    
    // 设置参数数量(根据变换类型: 刚体6, 仿射12)
    void SetNumberOfParameters(unsigned int num) { m_NumberOfParameters = num; }

    // =========== MIND特定参数 ===========
    // 设置MIND描述符半径（用于计算局部方差）
    void SetMINDRadius(unsigned int radius) { m_MINDRadius = radius; }
    unsigned int GetMINDRadius() const { return m_MINDRadius; }
    
    // 设置MIND的sigma参数（控制指数衰减）
    void SetMINDSigma(double sigma) { m_MINDSigma = sigma; }
    double GetMINDSigma() const { return m_MINDSigma; }
    
    // 设置邻域类型
    void SetNeighborhoodType(NeighborhoodType type) { m_NeighborhoodType = type; }
    NeighborhoodType GetNeighborhoodType() const { return m_NeighborhoodType; }
    void SetNeighborhoodTypeFromString(const std::string& typeStr);
    
    // =========== 采样参数 ===========
    void SetSamplingPercentage(double percent) { m_SamplingPercentage = percent; }
    double GetSamplingPercentage() const { return m_SamplingPercentage; }
    void SetRandomSeed(unsigned int seed) { m_RandomSeed = seed; m_UseFixedSeed = true; }
    
    // 掩膜设置 (用于局部配准)
    void SetFixedImageMask(MaskSpatialObjectType::Pointer mask) { m_FixedImageMask = mask; }
    MaskSpatialObjectType::Pointer GetFixedImageMask() const { return m_FixedImageMask; }
    bool HasFixedImageMask() const { return m_FixedImageMask.IsNotNull(); }
    
    // 采样策略设置
    void SetUseStratifiedSampling(bool use) { m_UseStratifiedSampling = use; }
    
    // 多线程设置
    void SetNumberOfThreads(unsigned int n) { m_NumberOfThreads = n; }
    unsigned int GetNumberOfThreads() const { return m_NumberOfThreads; }

    // 初始化
    void Initialize();
    
    // 重新采样(用于多分辨率)
    void ReinitializeSampling();
    
    // 显式清空缓存（用于级联配准阶段切换）
    void ResetCache();

    // 计算MIND-SSD值和梯度
    double GetValue();
    void GetDerivative(ParametersType& derivative);
    void GetValueAndDerivative(double& value, ParametersType& derivative);
    
    // =========== Gauss-Newton优化器接口 ===========
    // 获取残差向量: f[i] = fixedMIND[sample][channel] - movingMIND[sample][channel]
    // 大小: numValidSamples * numChannels
    void GetResiduals(std::vector<double>& residuals);
    
    // 获取雅可比矩阵: J[i][p] = ∂f[i]/∂q[p] = -∇MIND_moving · ∂T/∂q_p
    // 大小: (numValidSamples * numChannels) × numParameters
    void GetJacobian(std::vector<std::vector<double>>& jacobian);
    
    // 同时获取残差和雅可比矩阵(更高效,避免重复计算变换点)
    void GetResidualsAndJacobian(std::vector<double>& residuals,
                                  std::vector<std::vector<double>>& jacobian);

    // 获取当前度量值
    double GetCurrentValue() const { return m_CurrentValue; }
    
    // 获取有效采样点数量(用于调试)
    unsigned int GetNumberOfValidSamples() const { return m_NumberOfValidSamples; }
    
    // 计算图像的MIND特征图（公开供测试使用）
    void ComputeMINDFeatures(ImageType::Pointer image, 
                             std::vector<ImageType::Pointer>& mindFeatures);
    
    // 计算并返回中间 D_P (patch distance) 图
    void ComputePatchDistances(ImageType::Pointer image,
                                std::vector<ImageType::Pointer>& dpImages);
    
    // 兼容性接口：MIND不使用直方图
    void SetNumberOfHistogramBins(unsigned int /*bins*/) { }

private:
    // 图像指针
    ImageType::Pointer m_FixedImage;
    ImageType::Pointer m_MovingImage;
    InterpolatorType::Pointer m_Interpolator;
    TransformBaseType::Pointer m_Transform;
    
    // MIND特征图
    std::vector<ImageType::Pointer> m_FixedMINDFeatures;   // 每个邻域方向一个
    std::vector<ImageType::Pointer> m_MovingMINDFeatures;  // 每个邻域方向一个
    
    // 掩膜 (可选,用于局部配准)
    MaskSpatialObjectType::Pointer m_FixedImageMask;
    
    // 雅可比矩阵计算函数(外部提供)
    JacobianFunctionType m_JacobianFunction;
    unsigned int m_NumberOfParameters;

    // 移动图像梯度(用于梯度计算)
    std::array<ImageType::Pointer, 3> m_MovingImageGradient;
    
    // 预分配的MIND特征插值器(避免循环内重复创建)
    std::vector<InterpolatorType::Pointer> m_MovingMINDInterpolators;
    std::array<InterpolatorType::Pointer, 3> m_GradientInterpolators;
    
    // 移动图像MIND特征梯度（每个特征通道的x/y/z梯度）
    std::vector<std::array<ImageType::Pointer, 3>> m_MovingMINDFeatureGradients;
    std::vector<std::array<InterpolatorType::Pointer, 3>> m_MovingMINDFeatureGradientInterpolators;
    
    // 缓存机制：避免多分辨率中重复计算MIND特征
    ImageType::Pointer m_CachedFixedImage;
    ImageType::Pointer m_CachedMovingImage;
    bool m_FixedMINDFeaturesValid;
    bool m_MovingMINDFeaturesValid;

    // MIND参数
    unsigned int m_MINDRadius;     // MIND描述符计算半径
    double m_MINDSigma;            // 指数衰减参数
    NeighborhoodType m_NeighborhoodType;  // 邻域类型
    
    // 邻域偏移量（根据邻域类型初始化）
    std::vector<std::array<int, 3>> m_NeighborhoodOffsets;

    // 采样参数
    double m_SamplingPercentage;
    unsigned int m_RandomSeed;
    bool m_UseFixedSeed;
    bool m_UseStratifiedSampling;
    unsigned int m_NumberOfValidSamples;
    
    // 采样点信息
    struct SamplePoint
    {
        ImageType::PointType fixedPoint;     // 固定图像中的物理点
        ImageType::IndexType fixedIndex;     // 固定图像中的索引
        std::vector<float> fixedMINDValues;  // 固定图像MIND特征值
    };
    std::vector<SamplePoint> m_SamplePoints;

    // 当前度量值
    double m_CurrentValue;

    // 随机数生成器
    std::mt19937 m_RandomGenerator;
    bool m_Verbose;
    
    // 多线程参数
    unsigned int m_NumberOfThreads;
    
    // 有限差分步长(用于梯度计算)
    double m_FiniteDifferenceStep;

    // ============ 内部方法 ============
    
    // 初始化邻域偏移量
    void InitializeNeighborhoodOffsets();
    
    // 辅助函数：平移图像
    ImageType::Pointer ShiftImage(ImageType::Pointer image, int offsetX, int offsetY, int offsetZ);
    
    // 辅助函数：均值滤波（用于计算Patch内的平均值）
    ImageType::Pointer ApplyMeanFilter(ImageType::Pointer image);
    
    // 计算MIND特征梯度（用于解析梯度）
    void ComputeMINDFeatureGradients();
    
    // 采样策略
    void SampleFixedImage();
    void SampleFixedImageStratified();
    void SampleFixedImageRandom();
    
    // 计算MIND-SSD度量值
    double ComputeMINDSSD();
    
    // 计算有限差分梯度
    void ComputeFiniteDifferenceGradient(ParametersType& derivative);
    
    // 计算解析梯度（基于链式法则）
    void ComputeAnalyticalGradient(ParametersType& derivative);
    
    // 辅助函数：在给定变换参数下计算度量值
    double ComputeValueAtParameters(const ParametersType& parameters);
    
    // 将变换参数应用到变换对象
    void SetTransformParameters(const ParametersType& parameters);
    ParametersType GetTransformParameters() const;
};

#endif // MIND_METRIC_H
