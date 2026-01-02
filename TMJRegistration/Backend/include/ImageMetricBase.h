#ifndef IMAGE_METRIC_BASE_H
#define IMAGE_METRIC_BASE_H

#include <vector>
#include <memory>
#include <functional>
#include <array>
#include "itkImage.h"
#include "itkTransform.h"
#include "itkImageMaskSpatialObject.h"

/**
 * @brief 图像配准度量基类
 * 
 * 定义统一的度量接口，支持不同的相似性度量实现：
 * - MattesMutualInformation: Mattes互信息
 * - MINDMetric: MIND描述符
 * 
 * 所有派生类需要实现以下核心方法：
 * - GetValue(): 计算当前变换下的度量值
 * - GetDerivative(): 计算度量值对变换参数的梯度
 * - Initialize(): 初始化度量计算
 */
class ImageMetricBase
{
public:
    using ImageType = itk::Image<float, 3>;
    using MaskImageType = itk::Image<unsigned char, 3>;
    using MaskSpatialObjectType = itk::ImageMaskSpatialObject<3>;
    using TransformBaseType = itk::Transform<double, 3, 3>;
    using ParametersType = std::vector<double>;
    
    // 雅可比矩阵计算回调类型
    using JacobianFunctionType = std::function<void(const ImageType::PointType&, 
                                                     std::vector<std::array<double, 3>>&)>;

    ImageMetricBase() = default;
    virtual ~ImageMetricBase() = default;

    // =========== 核心接口 ===========
    
    // 设置固定图像和移动图像
    virtual void SetFixedImage(ImageType::Pointer fixedImage) = 0;
    virtual void SetMovingImage(ImageType::Pointer movingImage) = 0;
    
    // 设置变换
    virtual void SetTransform(TransformBaseType::Pointer transform) = 0;
    
    // 设置雅可比矩阵计算函数
    virtual void SetJacobianFunction(JacobianFunctionType func) = 0;
    
    // 设置参数数量
    virtual void SetNumberOfParameters(unsigned int num) = 0;
    
    // 初始化
    virtual void Initialize() = 0;
    
    // 重新采样（用于多分辨率）
    virtual void ReinitializeSampling() = 0;
    
    // 计算度量值
    virtual double GetValue() = 0;
    
    // 计算梯度
    virtual void GetDerivative(ParametersType& derivative) = 0;
    
    // 计算度量值和梯度
    virtual void GetValueAndDerivative(double& value, ParametersType& derivative) = 0;
    
    // 获取当前度量值
    virtual double GetCurrentValue() const = 0;
    
    // 获取有效采样点数量
    virtual unsigned int GetNumberOfValidSamples() const = 0;
    
    // =========== 通用设置接口 ===========
    
    // 掩膜设置
    virtual void SetFixedImageMask(MaskSpatialObjectType::Pointer mask) = 0;
    virtual MaskSpatialObjectType::Pointer GetFixedImageMask() const = 0;
    virtual bool HasFixedImageMask() const = 0;
    
    // 采样参数
    virtual void SetSamplingPercentage(double percent) = 0;
    virtual double GetSamplingPercentage() const = 0;
    virtual void SetRandomSeed(unsigned int seed) = 0;
    virtual void SetUseStratifiedSampling(bool use) = 0;
    
    // 多线程
    virtual void SetNumberOfThreads(unsigned int n) = 0;
    virtual unsigned int GetNumberOfThreads() const = 0;
    
    // 调试输出
    virtual void SetVerbose(bool v) = 0;
    virtual bool GetVerbose() const = 0;
    
    // =========== 可选的度量特定接口 ===========
    // 这些方法有默认空实现，具体度量可以覆盖
    
    // MI专用：直方图bin数量
    virtual void SetNumberOfHistogramBins(unsigned int /*bins*/) {}
    
    // MIND专用：描述符参数
    virtual void SetMINDRadius(unsigned int /*radius*/) {}
    virtual void SetMINDSigma(double /*sigma*/) {}
    virtual void SetMINDNeighborhoodType(const std::string& /*type*/) {}
};

#endif // IMAGE_METRIC_BASE_H
