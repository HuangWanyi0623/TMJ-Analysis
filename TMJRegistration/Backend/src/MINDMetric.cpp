#include "MINDMetric.h"
#include <iostream>
#include <iomanip>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <itkImageRegionConstIterator.h>
#include <itkImageRegionIterator.h>
#include <itkImageRegionIteratorWithIndex.h>
#include <itkGradientImageFilter.h>
#include <itkNeighborhoodIterator.h>
#include <itkConstNeighborhoodIterator.h>
#include <itkTranslationTransform.h>
#include <itkResampleImageFilter.h>
#include <itkLinearInterpolateImageFunction.h>
#include <itkMeanImageFilter.h>
#include <itkSubtractImageFilter.h>
#include <itkSquareImageFilter.h>
#include <itkAddImageFilter.h>
#include <itkMultiplyImageFilter.h>

// ============================================================================
// 构造函数和析构函数
// ============================================================================

MINDMetric::MINDMetric()
    : m_NumberOfParameters(6)
    , m_MINDRadius(1)
    , m_MINDSigma(0.8)
    , m_NeighborhoodType(NeighborhoodType::SixConnected)
    , m_SamplingPercentage(0.15)
    , m_RandomSeed(121212)
    , m_UseFixedSeed(true)
    , m_UseStratifiedSampling(true)
    , m_NumberOfValidSamples(0)
    , m_CurrentValue(0.0)
    , m_Verbose(false)
    , m_NumberOfThreads(std::thread::hardware_concurrency())
    , m_FiniteDifferenceStep(1e-4)
    , m_FixedMINDFeaturesValid(false)
    , m_MovingMINDFeaturesValid(false)
{
    // 初始化邻域偏移量
    InitializeNeighborhoodOffsets();
}

MINDMetric::~MINDMetric()
{
}

// ============================================================================
// 邻域初始化
// ============================================================================

void MINDMetric::InitializeNeighborhoodOffsets()
{
    m_NeighborhoodOffsets.clear();
    
    if (m_NeighborhoodType == NeighborhoodType::SixConnected)
    {
        // 6邻域: ±x, ±y, ±z
        m_NeighborhoodOffsets = {
            { 1,  0,  0},  // +x
            {-1,  0,  0},  // -x
            { 0,  1,  0},  // +y
            { 0, -1,  0},  // -y
            { 0,  0,  1},  // +z
            { 0,  0, -1}   // -z
        };
    }
    else // TwentySixConnected
    {
        // 26邻域: 3x3x3立方体排除中心
        for (int dz = -1; dz <= 1; ++dz)
        {
            for (int dy = -1; dy <= 1; ++dy)
            {
                for (int dx = -1; dx <= 1; ++dx)
                {
                    if (dx != 0 || dy != 0 || dz != 0)
                    {
                        m_NeighborhoodOffsets.push_back({dx, dy, dz});
                    }
                }
            }
        }
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Using " << m_NeighborhoodOffsets.size() 
                  << "-neighborhood" << std::endl;
    }
}

void MINDMetric::SetNeighborhoodTypeFromString(const std::string& typeStr)
{
    std::string lower = typeStr;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    
    if (lower.find("26") != std::string::npos || lower.find("twenty") != std::string::npos)
    {
        m_NeighborhoodType = NeighborhoodType::TwentySixConnected;
    }
    else
    {
        m_NeighborhoodType = NeighborhoodType::SixConnected;  // 默认6邻域
    }
    
    // 重新初始化邻域偏移量
    InitializeNeighborhoodOffsets();
}

// ============================================================================
// 图像设置
// ============================================================================

void MINDMetric::SetFixedImage(ImageType::Pointer fixedImage)
{
    m_FixedImage = fixedImage;
    // 图像改变时重置缓存标志，确保下次Initialize()重新计算MIND特征
    m_FixedMINDFeaturesValid = false;
}

void MINDMetric::SetMovingImage(ImageType::Pointer movingImage)
{
    m_MovingImage = movingImage;
    
    // 创建移动图像插值器
    m_Interpolator = InterpolatorType::New();
    m_Interpolator->SetInputImage(m_MovingImage);
    
    // 图像改变时重置缓存标志，确保下次Initialize()重新计算MIND特征
    m_MovingMINDFeaturesValid = false;
}

// ============================================================================
// 辅助函数: 平移图像
// ============================================================================

MINDMetric::ImageType::Pointer MINDMetric::ShiftImage(ImageType::Pointer image, 
                                                        int offsetX, int offsetY, int offsetZ)
{
    using TransformType = itk::TranslationTransform<double, 3>;
    using ResampleFilterType = itk::ResampleImageFilter<ImageType, ImageType>;
    using InterpolatorType = itk::LinearInterpolateImageFunction<ImageType, double>;
    
    auto transform = TransformType::New();
    TransformType::OutputVectorType translation;
    // ITK的Translation是物理坐标偏移，需要乘以spacing
    auto spacing = image->GetSpacing();
    translation[0] = -offsetX * spacing[0];  // 负号：平移方向相反
    translation[1] = -offsetY * spacing[1];
    translation[2] = -offsetZ * spacing[2];
    transform->Translate(translation);
    
    auto resampler = ResampleFilterType::New();
    resampler->SetTransform(transform);
    resampler->SetInput(image);
    resampler->SetSize(image->GetLargestPossibleRegion().GetSize());
    resampler->SetOutputOrigin(image->GetOrigin());
    resampler->SetOutputSpacing(image->GetSpacing());
    resampler->SetOutputDirection(image->GetDirection());
    resampler->SetDefaultPixelValue(0.0f);
    
    auto interpolator = InterpolatorType::New();
    resampler->SetInterpolator(interpolator);
    
    resampler->Update();
    return resampler->GetOutput();
}

// ============================================================================
// 辅助函数: 均值滤波 (计算Patch内的平均值)
// ============================================================================

MINDMetric::ImageType::Pointer MINDMetric::ApplyMeanFilter(ImageType::Pointer image)
{
    using MeanFilterType = itk::MeanImageFilter<ImageType, ImageType>;
    
    auto meanFilter = MeanFilterType::New();
    meanFilter->SetInput(image);
    
    // Patch半径由m_MINDRadius决定 (通常为1，即3x3x3 patch)
    ImageType::SizeType radius;
    radius.Fill(m_MINDRadius);
    meanFilter->SetRadius(radius);
    
    meanFilter->Update();
    return meanFilter->GetOutput();
}

// ============================================================================
// MIND特征计算 (正确实现)
// ============================================================================

void MINDMetric::ComputePatchDistances(ImageType::Pointer image,
                                        std::vector<ImageType::Pointer>& dpImages)
{
    dpImages.clear();
    dpImages.resize(m_NeighborhoodOffsets.size());
    
    ImageType::RegionType region = image->GetLargestPossibleRegion();
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Computing D_P (patch distances) only..." << std::endl;
    }
    
    // 计算所有方向的 D_P(x, x+r)
    for (size_t dir = 0; dir < m_NeighborhoodOffsets.size(); ++dir)
    {
        const auto& offset = m_NeighborhoodOffsets[dir];
        
        // 平移图像: I(x+r)
        ImageType::Pointer shiftedImage = ShiftImage(image, offset[0], offset[1], offset[2]);
        
        // 计算差值图: I(x) - I(x+r)
        using SubtractFilterType = itk::SubtractImageFilter<ImageType, ImageType, ImageType>;
        auto subtractFilter = SubtractFilterType::New();
        subtractFilter->SetInput1(image);
        subtractFilter->SetInput2(shiftedImage);
        subtractFilter->Update();
        
        // 计算平方差图: (I(x) - I(x+r))^2
        using SquareFilterType = itk::SquareImageFilter<ImageType, ImageType>;
        auto squareFilter = SquareFilterType::New();
        squareFilter->SetInput(subtractFilter->GetOutput());
        squareFilter->Update();
        
        // 对平方差图进行均值滤波，得到 D_P(x, x+r)
        dpImages[dir] = ApplyMeanFilter(squareFilter->GetOutput());
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] D_P images computed for " << dpImages.size() << " directions" << std::endl;
    }
}

void MINDMetric::ComputeMINDFeatures(ImageType::Pointer image, 
                                      std::vector<ImageType::Pointer>& mindFeatures)
{
    mindFeatures.clear();
    mindFeatures.resize(m_NeighborhoodOffsets.size());
    
    ImageType::RegionType region = image->GetLargestPossibleRegion();
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Computing patch-based MIND descriptors..." << std::endl;
        std::cout << "  Patch radius: " << m_MINDRadius << " (size: " 
                  << (2*m_MINDRadius+1) << "^3)" << std::endl;
    }
    
    // ========================================
    // 步骤1: 计算所有方向的 D_P(x, x+r)
    // ========================================
    std::vector<ImageType::Pointer> dpImages;
    ComputePatchDistances(image, dpImages);
    
    // ========================================
    // 步骤2: 计算方差 V(x) = (1/6) * sum(D_P)
    // ========================================
    ImageType::Pointer varianceImage = ImageType::New();
    varianceImage->SetRegions(region);
    varianceImage->SetSpacing(image->GetSpacing());
    varianceImage->SetOrigin(image->GetOrigin());
    varianceImage->SetDirection(image->GetDirection());
    varianceImage->Allocate();
    varianceImage->FillBuffer(0.0f);
    
    // 累加所有方向的 D_P
    using AddFilterType = itk::AddImageFilter<ImageType, ImageType, ImageType>;
    ImageType::Pointer sumImage = dpImages[0];
    for (size_t dir = 1; dir < dpImages.size(); ++dir)
    {
        auto addFilter = AddFilterType::New();
        addFilter->SetInput1(sumImage);
        addFilter->SetInput2(dpImages[dir]);
        addFilter->Update();
        sumImage = addFilter->GetOutput();
    }
    
    // 除以邻域数量得到平均值
    using IteratorType = itk::ImageRegionIterator<ImageType>;
    IteratorType varIt(varianceImage, region);
    IteratorType sumIt(sumImage, region);
    
    const float numDirections = static_cast<float>(m_NeighborhoodOffsets.size());
    for (varIt.GoToBegin(), sumIt.GoToBegin(); !varIt.IsAtEnd(); ++varIt, ++sumIt)
    {
        float avgDp = sumIt.Get() / numDirections;
        // V(x) = mean(D_P)，添加epsilon防止除零
        float variance = avgDp + 1e-10f;
        varIt.Set(variance);
    }
    
    if (m_Verbose)
    {
        std::cout << "  V(x) computed as mean of D_P over " << numDirections << " directions" << std::endl;
    }
    
    // ========================================
    // 步骤3: 计算 MIND(x,r) = exp(-D_P / V)
    // ========================================
    for (size_t dir = 0; dir < m_NeighborhoodOffsets.size(); ++dir)
    {
        mindFeatures[dir] = ImageType::New();
        mindFeatures[dir]->SetRegions(region);
        mindFeatures[dir]->SetSpacing(image->GetSpacing());
        mindFeatures[dir]->SetOrigin(image->GetOrigin());
        mindFeatures[dir]->SetDirection(image->GetDirection());
        mindFeatures[dir]->Allocate();
        
        IteratorType featureIt(mindFeatures[dir], region);
        IteratorType dpIt(dpImages[dir], region);
        IteratorType varIt2(varianceImage, region);
        
        for (featureIt.GoToBegin(), dpIt.GoToBegin(), varIt2.GoToBegin();
             !featureIt.IsAtEnd(); ++featureIt, ++dpIt, ++varIt2)
        {
            float dp = dpIt.Get();
            float variance = varIt2.Get();
            float mindValue = std::exp(-dp / variance);
            featureIt.Set(mindValue);
        }
    }
    
    // ========================================
    // 步骤4: 归一化 - 除以每个位置的最大值 (论文Eq.4: n是归一化常数使最大值为1)
    // ========================================
    ImageType::Pointer maxImage = ImageType::New();
    maxImage->SetRegions(region);
    maxImage->SetSpacing(image->GetSpacing());
    maxImage->SetOrigin(image->GetOrigin());
    maxImage->SetDirection(image->GetDirection());
    maxImage->Allocate();
    maxImage->FillBuffer(0.0f);
    
    using ConstIteratorType = itk::ImageRegionConstIterator<ImageType>;
    IteratorType maxIt(maxImage, region);
    for (maxIt.GoToBegin(); !maxIt.IsAtEnd(); ++maxIt)
    {
        ImageType::IndexType idx = maxIt.GetIndex();
        float maxVal = 0.0f;
        for (size_t dir = 0; dir < m_NeighborhoodOffsets.size(); ++dir)
        {
            float val = mindFeatures[dir]->GetPixel(idx);
            maxVal = std::max(maxVal, val);
        }
        maxIt.Set(maxVal + 1e-10f);  // 防止除零
    }
    
    // 归一化：mind = exp(-D_P/V) / max(exp(-D_P/V))
    for (size_t dir = 0; dir < m_NeighborhoodOffsets.size(); ++dir)
    {
        IteratorType featureIt(mindFeatures[dir], region);
        ConstIteratorType maxConstIt(maxImage, region);
        
        for (featureIt.GoToBegin(), maxConstIt.GoToBegin();
             !featureIt.IsAtEnd(); ++featureIt, ++maxConstIt)
        {
            float normalized = featureIt.Get() / maxConstIt.Get();
            featureIt.Set(normalized);
        }
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Successfully computed " << mindFeatures.size() 
                  << " MIND feature channels (with max normalization)" << std::endl;
    }
}

// ============================================================================
// MIND特征梯度计算
// ============================================================================

void MINDMetric::ComputeMINDFeatureGradients()
{
    m_MovingMINDFeatureGradients.clear();
    m_MovingMINDFeatureGradientInterpolators.clear();
    
    m_MovingMINDFeatureGradients.resize(m_MovingMINDFeatures.size());
    m_MovingMINDFeatureGradientInterpolators.resize(m_MovingMINDFeatures.size());
    
    using GradientFilterType = itk::GradientImageFilter<ImageType, float, float>;
    using GradientImageType = GradientFilterType::OutputImageType;
    
    for (size_t ch = 0; ch < m_MovingMINDFeatures.size(); ++ch)
    {
        auto gradientFilter = GradientFilterType::New();
        gradientFilter->SetInput(m_MovingMINDFeatures[ch]);
        gradientFilter->Update();
        
        GradientImageType::Pointer gradientImage = gradientFilter->GetOutput();
        
        // 分离梯度分量到独立的图像
        ImageType::RegionType region = m_MovingMINDFeatures[ch]->GetLargestPossibleRegion();
        
        for (unsigned int dim = 0; dim < 3; ++dim)
        {
            m_MovingMINDFeatureGradients[ch][dim] = ImageType::New();
            m_MovingMINDFeatureGradients[ch][dim]->SetRegions(region);
            m_MovingMINDFeatureGradients[ch][dim]->SetSpacing(m_MovingMINDFeatures[ch]->GetSpacing());
            m_MovingMINDFeatureGradients[ch][dim]->SetOrigin(m_MovingMINDFeatures[ch]->GetOrigin());
            m_MovingMINDFeatureGradients[ch][dim]->SetDirection(m_MovingMINDFeatures[ch]->GetDirection());
            m_MovingMINDFeatureGradients[ch][dim]->Allocate();
        }
        
        // 提取梯度分量
        using GradientIteratorType = itk::ImageRegionConstIterator<GradientImageType>;
        using OutputIteratorType = itk::ImageRegionIterator<ImageType>;
        
        GradientIteratorType gitInput(gradientImage, region);
        std::array<OutputIteratorType, 3> gitOutput = {
            OutputIteratorType(m_MovingMINDFeatureGradients[ch][0], region),
            OutputIteratorType(m_MovingMINDFeatureGradients[ch][1], region),
            OutputIteratorType(m_MovingMINDFeatureGradients[ch][2], region)
        };
        
        for (gitInput.GoToBegin(); !gitInput.IsAtEnd(); ++gitInput)
        {
            auto gradient = gitInput.Get();
            for (unsigned int dim = 0; dim < 3; ++dim)
            {
                gitOutput[dim].Set(gradient[dim]);
                ++gitOutput[dim];
            }
        }
        
        // 创建插值器
        for (unsigned int dim = 0; dim < 3; ++dim)
        {
            m_MovingMINDFeatureGradientInterpolators[ch][dim] = InterpolatorType::New();
            m_MovingMINDFeatureGradientInterpolators[ch][dim]->SetInputImage(
                m_MovingMINDFeatureGradients[ch][dim]);
        }
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Computed gradients for " << m_MovingMINDFeatures.size() 
                  << " feature channels" << std::endl;
    }
}

// ============================================================================
// 初始化
// ============================================================================

void MINDMetric::Initialize()
{
    if (!m_FixedImage || !m_MovingImage)
    {
        throw std::runtime_error("[MIND] Fixed and moving images must be set before initialization");
    }
    
    if (!m_Transform)
    {
        throw std::runtime_error("[MIND] Transform must be set before initialization");
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Initializing MIND metric..." << std::endl;
        std::cout << "  Radius: " << m_MINDRadius << std::endl;
        std::cout << "  Sigma: " << m_MINDSigma << std::endl;
    }
    
    // 初始化邻域偏移量（根据固定图像的尺寸和spacing动态调整）
    InitializeNeighborhoodOffsets();
    
    // 【性能关键】检查固定图像是否改变，避免重复计算
    bool fixedImageChanged = (m_CachedFixedImage != m_FixedImage);
    if (fixedImageChanged || !m_FixedMINDFeaturesValid)
    {
        if (m_Verbose)
        {
            std::cout << "[MIND] Computing MIND features for fixed image..." << std::endl;
        }
        ComputeMINDFeatures(m_FixedImage, m_FixedMINDFeatures);
        m_CachedFixedImage = m_FixedImage;
        m_FixedMINDFeaturesValid = true;
    }
    else
    {
        if (m_Verbose)
        {
            std::cout << "[MIND] Using cached MIND features for fixed image" << std::endl;
        }
    }
    
    // 【性能关键】检查移动图像是否改变
    bool movingImageChanged = (m_CachedMovingImage != m_MovingImage);
    if (movingImageChanged || !m_MovingMINDFeaturesValid)
    {
        if (m_Verbose)
        {
            std::cout << "[MIND] Computing MIND features for moving image..." << std::endl;
        }
        ComputeMINDFeatures(m_MovingImage, m_MovingMINDFeatures);
        
        // 计算移动图像MIND特征的梯度（用于解析梯度计算）
        ComputeMINDFeatureGradients();
        
        // 【性能关键】预创建所有移动MIND特征的插值器
        m_MovingMINDInterpolators.clear();
        m_MovingMINDInterpolators.resize(m_MovingMINDFeatures.size());
        for (size_t ch = 0; ch < m_MovingMINDFeatures.size(); ++ch)
        {
            m_MovingMINDInterpolators[ch] = InterpolatorType::New();
            m_MovingMINDInterpolators[ch]->SetInputImage(m_MovingMINDFeatures[ch]);
        }
        
        if (m_Verbose)
        {
            std::cout << "[MIND] Pre-allocated " << m_MovingMINDInterpolators.size() 
                      << " interpolators for MIND features" << std::endl;
        }
        
        m_CachedMovingImage = m_MovingImage;
        m_MovingMINDFeaturesValid = true;
    }
    else
    {
        if (m_Verbose)
        {
            std::cout << "[MIND] Using cached MIND features for moving image" << std::endl;
        }
    }
    
    // 采样固定图像
    SampleFixedImage();
    
    // 初始化随机数生成器
    if (m_UseFixedSeed)
    {
        m_RandomGenerator.seed(m_RandomSeed);
    }
    else
    {
        std::random_device rd;
        m_RandomGenerator.seed(rd());
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Initialization complete. Samples: " 
                  << m_SamplePoints.size() << std::endl;
    }
}

void MINDMetric::ReinitializeSampling()
{
    // 重新计算移动图像MIND特征
    ComputeMINDFeatures(m_MovingImage, m_MovingMINDFeatures);
    
    // 重新计算梯度
    ComputeMINDFeatureGradients();
    
    // 重新采样
    SampleFixedImage();
}

void MINDMetric::ResetCache()
{
    // 显式清空所有缓存状态，强制下次Initialize()重新计算MIND特征
    m_CachedFixedImage = nullptr;
    m_CachedMovingImage = nullptr;
    m_FixedMINDFeaturesValid = false;
    m_MovingMINDFeaturesValid = false;
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Cache reset - next Initialize() will recompute all MIND features" << std::endl;
    }
}

// ============================================================================
// 采样策略
// ============================================================================

void MINDMetric::SampleFixedImage()
{
    if (m_UseStratifiedSampling)
    {
        SampleFixedImageStratified();
    }
    else
    {
        SampleFixedImageRandom();
    }
}

void MINDMetric::SampleFixedImageStratified()
{
    m_SamplePoints.clear();
    
    ImageType::RegionType region = m_FixedImage->GetLargestPossibleRegion();
    ImageType::SizeType size = region.GetSize();
    
    // 计算目标采样数
    unsigned long totalVoxels = size[0] * size[1] * size[2];
    unsigned long targetSamples = static_cast<unsigned long>(totalVoxels * m_SamplingPercentage);
    
    // 计算采样间隔
    double samplingInterval = std::cbrt(static_cast<double>(totalVoxels) / targetSamples);
    unsigned int step = std::max(1u, static_cast<unsigned int>(samplingInterval));
    
    // 边界填充（避免采样到MIND计算边界外）
    unsigned int padding = m_MINDRadius + 1;
    
    // 预分配空间避免频繁reallocation
    m_SamplePoints.reserve(targetSamples);
    
    for (unsigned int z = padding; z < size[2] - padding; z += step)
    {
        for (unsigned int y = padding; y < size[1] - padding; y += step)
        {
            for (unsigned int x = padding; x < size[0] - padding; x += step)
            {
                // 【添加上限控制】参考MattesMutualInformation实现
                if (m_SamplePoints.size() >= targetSamples)
                {
                    goto sampling_complete;
                }
                
                ImageType::IndexType index;
                index[0] = x;
                index[1] = y;
                index[2] = z;
                
                // 如果有掩膜，检查点是否在掩膜内
                ImageType::PointType point;
                m_FixedImage->TransformIndexToPhysicalPoint(index, point);
                
                if (m_FixedImageMask.IsNotNull())
                {
                    if (!m_FixedImageMask->IsInsideInObjectSpace(point))
                    {
                        continue;
                    }
                }
                
                // 创建采样点
                SamplePoint sample;
                sample.fixedPoint = point;
                sample.fixedIndex = index;
                
                // 获取固定图像MIND特征值
                sample.fixedMINDValues.resize(m_FixedMINDFeatures.size());
                for (size_t ch = 0; ch < m_FixedMINDFeatures.size(); ++ch)
                {
                    sample.fixedMINDValues[ch] = m_FixedMINDFeatures[ch]->GetPixel(index);
                }
                
                m_SamplePoints.push_back(sample);
            }
        }
    }
    
sampling_complete:
    if (m_Verbose)
    {
        std::cout << "[MIND] Stratified sampling: " << m_SamplePoints.size() 
                  << " samples (target: " << targetSamples << ")" << std::endl;
    }
}

void MINDMetric::SampleFixedImageRandom()
{
    m_SamplePoints.clear();
    
    ImageType::RegionType region = m_FixedImage->GetLargestPossibleRegion();
    ImageType::SizeType size = region.GetSize();
    
    // 计算目标采样数
    unsigned long totalVoxels = size[0] * size[1] * size[2];
    unsigned long targetSamples = static_cast<unsigned long>(totalVoxels * m_SamplingPercentage);
    
    // 边界填充
    unsigned int padding = m_MINDRadius + 1;
    
    // 创建随机分布
    std::uniform_int_distribution<unsigned int> distX(padding, size[0] - padding - 1);
    std::uniform_int_distribution<unsigned int> distY(padding, size[1] - padding - 1);
    std::uniform_int_distribution<unsigned int> distZ(padding, size[2] - padding - 1);
    
    unsigned long attempts = 0;
    unsigned long maxAttempts = targetSamples * 3;  // 最大尝试次数
    
    while (m_SamplePoints.size() < targetSamples && attempts < maxAttempts)
    {
        ++attempts;
        
        ImageType::IndexType index;
        index[0] = distX(m_RandomGenerator);
        index[1] = distY(m_RandomGenerator);
        index[2] = distZ(m_RandomGenerator);
        
        ImageType::PointType point;
        m_FixedImage->TransformIndexToPhysicalPoint(index, point);
        
        // 如果有掩膜，检查点是否在掩膜内
        if (m_FixedImageMask.IsNotNull())
        {
            if (!m_FixedImageMask->IsInsideInObjectSpace(point))
            {
                continue;
            }
        }
        
        // 创建采样点
        SamplePoint sample;
        sample.fixedPoint = point;
        sample.fixedIndex = index;
        
        // 获取固定图像MIND特征值
        sample.fixedMINDValues.resize(m_FixedMINDFeatures.size());
        for (size_t ch = 0; ch < m_FixedMINDFeatures.size(); ++ch)
        {
            sample.fixedMINDValues[ch] = m_FixedMINDFeatures[ch]->GetPixel(index);
        }
        
        m_SamplePoints.push_back(sample);
    }
    
    if (m_Verbose)
    {
        std::cout << "[MIND] Random sampling: " << m_SamplePoints.size() 
                  << " samples (target: " << targetSamples << ")" << std::endl;
    }
}

// ============================================================================
// MIND-SSD度量计算
// ============================================================================

double MINDMetric::ComputeMINDSSD()
{
    double totalSSD = 0.0;
    unsigned int validCount = 0;
    
    const size_t numSamples = m_SamplePoints.size();
    const size_t numChannels = m_MovingMINDFeatures.size();
    
    // OpenMP并行化采样点遍历,使用reduction子句
    #pragma omp parallel for schedule(static) reduction(+:totalSSD) reduction(+:validCount) if(numSamples > 1000)
    for (int i = 0; i < static_cast<int>(numSamples); ++i)
    {
        const auto& sample = m_SamplePoints[i];
        
        // 变换固定图像点到移动图像空间
        ImageType::PointType transformedPoint = m_Transform->TransformPoint(sample.fixedPoint);
        
        bool allChannelsValid = true;
        double sampleSSD = 0.0;
        
        // 遍历所有MIND特征通道
        for (size_t ch = 0; ch < numChannels; ++ch)
        {
            // 【关键优化】使用预分配的插值器,避免循环内New()
            if (m_MovingMINDInterpolators[ch]->IsInsideBuffer(transformedPoint))
            {
                double movingMINDValue = m_MovingMINDInterpolators[ch]->Evaluate(transformedPoint);
                double diff = sample.fixedMINDValues[ch] - movingMINDValue;
                sampleSSD += diff * diff;
            }
            else
            {
                allChannelsValid = false;
                break;
            }
        }
        
        if (allChannelsValid)
        {
            totalSSD += sampleSSD;
            validCount++;
        }
    }
    
    m_NumberOfValidSamples = validCount;
    
    // 归一化：除以有效采样点数和通道数
    double ssdValue = 0.0;
    if (m_NumberOfValidSamples > 0)
    {
        ssdValue = totalSSD / (m_NumberOfValidSamples * numChannels);
    }
    
    return ssdValue;
}

double MINDMetric::GetValue()
{
    m_CurrentValue = ComputeMINDSSD();
    return m_CurrentValue;
}

// ============================================================================
// 梯度计算
// ============================================================================

void MINDMetric::GetDerivative(ParametersType& derivative)
{
    derivative.resize(m_NumberOfParameters, 0.0);
    
    // 使用解析梯度（如果提供了雅可比函数）或有限差分
    if (m_JacobianFunction)
    {
        ComputeAnalyticalGradient(derivative);
    }
    else
    {
        ComputeFiniteDifferenceGradient(derivative);
    }
}

void MINDMetric::GetValueAndDerivative(double& value, ParametersType& derivative)
{
    value = GetValue();
    GetDerivative(derivative);
}

// ============================================================================
// Gauss-Newton优化器接口
// ============================================================================

void MINDMetric::GetResiduals(std::vector<double>& residuals)
{
    const size_t numSamples = m_SamplePoints.size();
    const size_t numChannels = m_MovingMINDFeatures.size();
    
    // 预分配空间: numSamples * numChannels
    residuals.clear();
    residuals.reserve(numSamples * numChannels);
    
    unsigned int validCount = 0;
    
    for (size_t i = 0; i < numSamples; ++i)
    {
        const auto& sample = m_SamplePoints[i];
        
        // 变换固定图像点到移动图像空间
        ImageType::PointType transformedPoint = m_Transform->TransformPoint(sample.fixedPoint);
        
        // 检查所有通道是否有效
        bool allChannelsValid = true;
        for (size_t ch = 0; ch < numChannels; ++ch)
        {
            if (!m_MovingMINDInterpolators[ch]->IsInsideBuffer(transformedPoint))
            {
                allChannelsValid = false;
                break;
            }
        }
        
        if (allChannelsValid)
        {
            // 计算每个通道的残差: f = fixed - moving
            for (size_t ch = 0; ch < numChannels; ++ch)
            {
                double movingMINDValue = m_MovingMINDInterpolators[ch]->Evaluate(transformedPoint);
                double residual = sample.fixedMINDValues[ch] - movingMINDValue;
                residuals.push_back(residual);
            }
            ++validCount;
        }
    }
    
    m_NumberOfValidSamples = validCount;
}

void MINDMetric::GetJacobian(std::vector<std::vector<double>>& jacobian)
{
    std::vector<double> residuals;
    GetResidualsAndJacobian(residuals, jacobian);
}

void MINDMetric::GetResidualsAndJacobian(std::vector<double>& residuals,
                                          std::vector<std::vector<double>>& jacobian)
{
    if (!m_JacobianFunction)
    {
        throw std::runtime_error("[MIND] Jacobian function must be set for Gauss-Newton optimization");
    }
    
    const size_t numSamples = m_SamplePoints.size();
    const size_t numChannels = m_MovingMINDFeatures.size();
    const size_t numParams = m_NumberOfParameters;
    
    // 清空并预分配
    residuals.clear();
    jacobian.clear();
    residuals.reserve(numSamples * numChannels);
    jacobian.reserve(numSamples * numChannels);
    
    unsigned int validCount = 0;
    
    for (size_t i = 0; i < numSamples; ++i)
    {
        const auto& sample = m_SamplePoints[i];
        
        // 变换固定图像点到移动图像空间
        ImageType::PointType transformedPoint = m_Transform->TransformPoint(sample.fixedPoint);
        
        // 检查所有通道和梯度是否有效
        bool allValid = true;
        for (size_t ch = 0; ch < numChannels; ++ch)
        {
            if (!m_MovingMINDInterpolators[ch]->IsInsideBuffer(transformedPoint))
            {
                allValid = false;
                break;
            }
            for (unsigned int dim = 0; dim < 3; ++dim)
            {
                if (!m_MovingMINDFeatureGradientInterpolators[ch][dim]->IsInsideBuffer(transformedPoint))
                {
                    allValid = false;
                    break;
                }
            }
            if (!allValid) break;
        }
        
        if (!allValid)
        {
            continue;
        }
        
        // 获取变换的雅可比矩阵 ∂T/∂q: [numParams][3]
        std::vector<std::array<double, 3>> transformJacobian;
        m_JacobianFunction(sample.fixedPoint, transformJacobian);
        
        // 对每个通道计算残差和雅可比
        for (size_t ch = 0; ch < numChannels; ++ch)
        {
            // 残差: f = fixed - moving
            double movingMINDValue = m_MovingMINDInterpolators[ch]->Evaluate(transformedPoint);
            double residual = sample.fixedMINDValues[ch] - movingMINDValue;
            residuals.push_back(residual);
            
            // MIND特征的空间梯度 ∇MIND_moving
            std::array<double, 3> mindGradient;
            for (unsigned int dim = 0; dim < 3; ++dim)
            {
                mindGradient[dim] = m_MovingMINDFeatureGradientInterpolators[ch][dim]->Evaluate(transformedPoint);
            }
            
            // 雅可比矩阵行: J[row][p] = ∂f/∂q_p = -∇MIND · ∂T/∂q_p
            // 注意负号: f = fixed - moving, ∂f/∂q = -∂moving/∂q = -∇MIND · ∂T/∂q
            std::vector<double> jacobianRow(numParams, 0.0);
            for (size_t p = 0; p < numParams; ++p)
            {
                double dotProduct = 0.0;
                for (unsigned int dim = 0; dim < 3; ++dim)
                {
                    dotProduct += mindGradient[dim] * transformJacobian[p][dim];
                }
                jacobianRow[p] = -dotProduct;  // 负号!
            }
            jacobian.push_back(jacobianRow);
        }
        
        ++validCount;
    }
    
    m_NumberOfValidSamples = validCount;
    
    if (m_Verbose && validCount > 0)
    {
        std::cout << "[MIND] Gauss-Newton: " << residuals.size() << " residuals, "
                  << validCount << " valid samples" << std::endl;
    }
}

void MINDMetric::ComputeFiniteDifferenceGradient(ParametersType& derivative)
{
    derivative.resize(m_NumberOfParameters, 0.0);
    
    // 保存当前参数
    ParametersType currentParams = GetTransformParameters();
    double currentValue = GetValue();
    
    // 对每个参数计算有限差分
    for (unsigned int p = 0; p < m_NumberOfParameters; ++p)
    {
        ParametersType perturbedParams = currentParams;
        perturbedParams[p] += m_FiniteDifferenceStep;
        
        SetTransformParameters(perturbedParams);
        double perturbedValue = ComputeMINDSSD();
        
        // 前向差分
        derivative[p] = (perturbedValue - currentValue) / m_FiniteDifferenceStep;
    }
    
    // 恢复原始参数
    SetTransformParameters(currentParams);
}

void MINDMetric::ComputeAnalyticalGradient(ParametersType& derivative)
{
    derivative.resize(m_NumberOfParameters, 0.0);
    
    if (!m_JacobianFunction)
    {
        std::cerr << "[MIND] Warning: Jacobian function not set, using finite difference" << std::endl;
        ComputeFiniteDifferenceGradient(derivative);
        return;
    }
    
    std::vector<double> localDerivative(m_NumberOfParameters, 0.0);
    unsigned int validSamples = 0;
    
    const size_t numSamples = m_SamplePoints.size();
    const size_t numChannels = m_MovingMINDFeatures.size();
    
    // 使用临界区保护梯度累加
    #pragma omp parallel if(numSamples > 1000)
    {
        std::vector<double> threadDerivative(m_NumberOfParameters, 0.0);
        unsigned int threadValidSamples = 0;
        
        #pragma omp for schedule(static) nowait
        for (int i = 0; i < static_cast<int>(numSamples); ++i)
        {
            const auto& sample = m_SamplePoints[i];
            
            ImageType::PointType transformedPoint = m_Transform->TransformPoint(sample.fixedPoint);
            
            // 获取雅可比矩阵
            std::vector<std::array<double, 3>> jacobian;
            m_JacobianFunction(sample.fixedPoint, jacobian);
            
            bool isValid = true;
            std::vector<double> channelGradients(m_NumberOfParameters, 0.0);
            
            for (size_t ch = 0; ch < numChannels && isValid; ++ch)
            {
                // 【关键优化】使用预分配的插值器
                if (!m_MovingMINDInterpolators[ch]->IsInsideBuffer(transformedPoint))
                {
                    isValid = false;
                    break;
                }
                
                // 检查梯度插值器
                bool gradientValid = true;
                for (unsigned int dim = 0; dim < 3; ++dim)
                {
                    if (!m_MovingMINDFeatureGradientInterpolators[ch][dim]->IsInsideBuffer(transformedPoint))
                    {
                        gradientValid = false;
                        break;
                    }
                }
                
                if (!gradientValid)
                {
                    isValid = false;
                    break;
                }
                
                double movingMINDValue = m_MovingMINDInterpolators[ch]->Evaluate(transformedPoint);
                double diff = sample.fixedMINDValues[ch] - movingMINDValue;
                
                // 获取MIND特征梯度
                std::array<double, 3> mindGradient;
                for (unsigned int dim = 0; dim < 3; ++dim)
                {
                    mindGradient[dim] = m_MovingMINDFeatureGradientInterpolators[ch][dim]->Evaluate(transformedPoint);
                }
                
                // d(SSD)/dp = -2 * (F - M) * ∇M * dT/dp
                for (unsigned int p = 0; p < m_NumberOfParameters; ++p)
                {
                    double dotProduct = 0.0;
                    for (unsigned int dim = 0; dim < 3; ++dim)
                    {
                        dotProduct += mindGradient[dim] * jacobian[p][dim];
                    }
                    channelGradients[p] += -2.0 * diff * dotProduct;
                }
            }
            
            if (isValid)
            {
                for (unsigned int p = 0; p < m_NumberOfParameters; ++p)
                {
                    threadDerivative[p] += channelGradients[p];
                }
                ++threadValidSamples;
            }
        }
        
        // 合并线程结果
        #pragma omp critical
        {
            for (unsigned int p = 0; p < m_NumberOfParameters; ++p)
            {
                localDerivative[p] += threadDerivative[p];
            }
            validSamples += threadValidSamples;
        }
    }
    
    // 归一化
    if (validSamples > 0)
    {
        double normFactor = 1.0 / (validSamples * numChannels);
        for (unsigned int p = 0; p < m_NumberOfParameters; ++p)
        {
            derivative[p] = localDerivative[p] * normFactor;
        }
    }
}

// ============================================================================
// 参数辅助函数
// ============================================================================

MINDMetric::ParametersType MINDMetric::GetTransformParameters() const
{
    if (!m_Transform)
    {
        return ParametersType();
    }
    
    auto itkParams = m_Transform->GetParameters();
    ParametersType params(itkParams.Size());
    for (unsigned int i = 0; i < itkParams.Size(); ++i)
    {
        params[i] = itkParams[i];
    }
    return params;
}

void MINDMetric::SetTransformParameters(const ParametersType& parameters)
{
    if (!m_Transform || parameters.size() != m_Transform->GetNumberOfParameters())
    {
        return;
    }
    
    itk::Array<double> itkParams(parameters.size());
    for (size_t i = 0; i < parameters.size(); ++i)
    {
        itkParams[i] = parameters[i];
    }
    m_Transform->SetParameters(itkParams);
}

double MINDMetric::ComputeValueAtParameters(const ParametersType& parameters)
{
    SetTransformParameters(parameters);
    return ComputeMINDSSD();
}
