#ifndef CONFIG_MANAGER_H
#define CONFIG_MANAGER_H

#include <string>
#include <vector>
#include <map>
#include <fstream>
#include <sstream>
#include <iostream>
#include <stdexcept>

/**
 * @brief 配置管理器 - 轻量级JSON解析
 * 
 * 支持从JSON文件读取配准参数
 * 不依赖第三方库,使用简单的手写解析器
 * 
 * 支持的数据类型:
 * - 数值 (int, double)
 * - 字符串
 * - 数组 (用于shrinkFactors, smoothingSigmas等)
 * 
 * 支持的度量类型:
 * - MattesMutualInformation (互信息, 默认)
 * - MIND (Modality Independent Neighbourhood Descriptor)
 */
class ConfigManager
{
public:
    // 变换类型枚举
    enum class TransformType
    {
        Rigid,           // 刚体变换 (6参数)
        Affine,          // 仿射变换 (12参数)
        RigidThenAffine  // 级联变换: 先刚体后仿射 (自动两阶段)
    };
    
    // 度量类型枚举
    enum class MetricType
    {
        MattesMutualInformation,  // Mattes互信息 (默认)
        MIND                      // MIND描述符
    };
    
    // 优化器类型枚举
    enum class OptimizerType
    {
        RegularStepGradientDescent,  // 规则步长梯度下降 (默认,MI推荐)
        GaussNewton                   // Gauss-Newton优化器 (MIND推荐)
    };
    
    // 配置参数结构
    struct RegistrationConfig
    {
        // 变换类型
        TransformType transformType = TransformType::Rigid;
        
        // 度量类型
        MetricType metricType = MetricType::MattesMutualInformation;
        
        // 优化器类型
        OptimizerType optimizerType = OptimizerType::RegularStepGradientDescent;
        
        // 度量参数 (MI专用)
        unsigned int numberOfHistogramBins = 32;
        unsigned int numberOfSpatialSamples = 0; // deprecated if samplingPercentage is used
        double samplingPercentage = 0.25; // 25% sampling by default
        
        // MIND度量参数
        unsigned int mindRadius = 1;           // MIND描述符计算半径
        double mindSigma = 0.8;                // MIND指数衰减参数
        std::string mindNeighborhoodType = "6-connected";  // 邻域类型: "6-connected" 或 "26-connected"
        
        // 优化器参数
        std::vector<double> learningRate = {2.0, 1.0, 0.5, 0.1, 0.05};  // Per-level learning rates
        double minimumStepLength = 1e-6;
        std::vector<unsigned int> numberOfIterations = {1000, 500, 250, 100, 0};  // ANTs 5-layer pyramid
        double relaxationFactor = 0.5;
        double gradientMagnitudeTolerance = 1e-6;
        
        // Gauss-Newton特有参数
        bool useLineSearch = true;            // 是否使用线搜索
        bool useLevenbergMarquardt = true;    // 是否使用L-M阻尼
        double dampingFactor = 1e-3;          // L-M初始阻尼因子
        
        // 多分辨率参数
        unsigned int numberOfLevels = 5;
        std::vector<unsigned int> shrinkFactors = {12, 8, 4, 2, 1};
        std::vector<double> smoothingSigmas = {4.0, 3.0, 2.0, 1.0, 1.0};
        
        // 采样策略
        bool useStratifiedSampling = true;
        unsigned int randomSeed = 121212;
    };

    ConfigManager();
    ~ConfigManager();

    // 从JSON文件加载配置
    bool LoadFromFile(const std::string& filePath);
    
    // 保存配置到JSON文件 (用于生成默认配置)
    bool SaveToFile(const std::string& filePath) const;
    
    // 创建默认配置文件
    static bool CreateDefaultConfigFile(const std::string& filePath, TransformType type = TransformType::Rigid);
    
    // 获取配置
    const RegistrationConfig& GetConfig() const { return m_Config; }
    RegistrationConfig& GetConfig() { return m_Config; }
    
    // 设置配置值
    void SetTransformType(TransformType type) { m_Config.transformType = type; }
    void SetTransformType(const std::string& typeStr);
    void SetMetricType(MetricType type) { m_Config.metricType = type; }
    void SetMetricType(const std::string& typeStr);
    void SetOptimizerType(OptimizerType type) { m_Config.optimizerType = type; }
    void SetOptimizerType(const std::string& typeStr);
    
    // 获取变换类型字符串
    static std::string TransformTypeToString(TransformType type);
    static TransformType StringToTransformType(const std::string& str);
    
    // 获取度量类型字符串
    static std::string MetricTypeToString(MetricType type);
    static MetricType StringToMetricType(const std::string& str);
    
    // 获取优化器类型字符串
    static std::string OptimizerTypeToString(OptimizerType type);
    static OptimizerType StringToOptimizerType(const std::string& str);
    
    // 打印配置信息
    void PrintConfig() const;

private:
    RegistrationConfig m_Config;
    
    // 简单JSON解析辅助函数
    std::string Trim(const std::string& str) const;
    bool ParseJsonFile(const std::string& content);
    std::string ExtractValue(const std::string& content, const std::string& key) const;
    std::vector<std::string> ExtractArray(const std::string& content, const std::string& key) const;
    
    // JSON生成辅助
    std::string GenerateJson() const;
};

#endif // CONFIG_MANAGER_H
