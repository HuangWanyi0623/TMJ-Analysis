/**
 * @brief 简化的 MIND 特征测试程序 - 输出 D_P (patch distance) 图
 * 
 * 目的：验证 MIND 实现是否正确，通过对比 D_P 图与论文 Fig. 1
 * 
 * 使用方法：
 * TestMINDSimple.exe <fixed> <moving> <output_prefix>
 * 
 * 输出D_P图（对比论文）和最终MIND特征
 */

#include <iostream>
#include <string>
#include <vector>
#include "itkImage.h"
#include "itkImageFileReader.h"
#include "itkImageFileWriter.h"
#include "MINDMetric.h"

using ImageType = itk::Image<float, 3>;

int main(int argc, char* argv[])
{
    if (argc < 4)
    {
        std::cout << "\n=== MIND Feature Test (Simplified) ===\n" << std::endl;
        std::cout << "Usage: " << argv[0] << " <fixed> <moving> <output_prefix>\n" << std::endl;
        std::cout << "Output:" << std::endl;
        std::cout << "  *_dp_ch*.nrrd   - D_P (patch distance) images (compare with paper)" << std::endl;
        std::cout << "  *_mind_ch*.nrrd - Final MIND features\n" << std::endl;
        std::cout << "IMPORTANT: Use full 3D volumes, NOT thin ROI slices!\n" << std::endl;
        return EXIT_FAILURE;
    }
    
    std::string fixedPath = argv[1];
    std::string movingPath = argv[2];
    std::string outputPrefix = argv[3];
    
    std::cout << "\n[1/4] Loading images..." << std::endl;
    
    // 加载固定图像
    using ReaderType = itk::ImageFileReader<ImageType>;
    auto fixedReader = ReaderType::New();
    fixedReader->SetFileName(fixedPath);
    try { fixedReader->Update(); }
    catch (const itk::ExceptionObject& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        return EXIT_FAILURE;
    }
    
    // 加载移动图像
    auto movingReader = ReaderType::New();
    movingReader->SetFileName(movingPath);
    try { movingReader->Update(); }
    catch (const itk::ExceptionObject& e)
    {
        std::cerr << "Error: " << e.what() << std::endl;
        return EXIT_FAILURE;
    }
    
    auto fixedImage = fixedReader->GetOutput();
    auto movingImage = movingReader->GetOutput();
    
    std::cout << "  Fixed:  " << fixedImage->GetLargestPossibleRegion().GetSize() << std::endl;
    std::cout << "  Moving: " << movingImage->GetLargestPossibleRegion().GetSize() << std::endl;
    
    // 检查图像尺寸
    auto movingSize = movingImage->GetLargestPossibleRegion().GetSize();
    if (movingSize[2] < 32)
    {
        std::cout << "\n[WARNING] Moving image has only " << movingSize[2] << " slices!" << std::endl;
        std::cout << "  MIND requires full 3D context. Use complete volumes (100+ slices).\n" << std::endl;
    }
    
    // 创建 MIND 度量
    std::cout << "\n[2/4] Initializing MIND..." << std::endl;
    auto mindMetric = std::make_unique<MINDMetric>();
    mindMetric->SetMINDRadius(1);
    mindMetric->SetMINDSigma(0.8);
    mindMetric->SetNeighborhoodTypeFromString("6-connected");
    mindMetric->SetVerbose(true);
    
    // 计算 D_P 图 (patch distance)
    std::cout << "\n[3/4] Computing D_P (patch distance) images..." << std::endl;
    std::vector<ImageType::Pointer> fixedDp, movingDp;
    mindMetric->ComputePatchDistances(fixedImage, fixedDp);
    mindMetric->ComputePatchDistances(movingImage, movingDp);
    
    // 计算最终 MIND 特征
    std::vector<ImageType::Pointer> fixedMind, movingMind;
    mindMetric->ComputeMINDFeatures(fixedImage, fixedMind);
    mindMetric->ComputeMINDFeatures(movingImage, movingMind);
    
    // 保存文件
    std::cout << "\n[4/4] Saving outputs..." << std::endl;
    using WriterType = itk::ImageFileWriter<ImageType>;
    auto writer = WriterType::New();
    
    // 保存 D_P 图
    std::cout << "  Saving D_P images (patch distance - compare with paper Fig. 1)..." << std::endl;
    for (size_t ch = 0; ch < fixedDp.size(); ++ch)
    {
        std::string fname = outputPrefix + "_fixed_dp_ch" + std::to_string(ch) + ".nrrd";
        writer->SetFileName(fname);
        writer->SetInput(fixedDp[ch]);
        try { writer->Update(); std::cout << "    " << fname << std::endl; }
        catch (...) {}
    }
    
    for (size_t ch = 0; ch < movingDp.size(); ++ch)
    {
        std::string fname = outputPrefix + "_moving_dp_ch" + std::to_string(ch) + ".nrrd";
        writer->SetFileName(fname);
        writer->SetInput(movingDp[ch]);
        try { writer->Update(); std::cout << "    " << fname << std::endl; }
        catch (...) {}
    }
    
    // 保存 MIND 特征
    std::cout << "\n  Saving MIND features (exp(-D_P/V))..." << std::endl;
    for (size_t ch = 0; ch < fixedMind.size(); ++ch)
    {
        std::string fname = outputPrefix + "_fixed_mind_ch" + std::to_string(ch) + ".nrrd";
        writer->SetFileName(fname);
        writer->SetInput(fixedMind[ch]);
        try { writer->Update(); std::cout << "    " << fname << std::endl; }
        catch (...) {}
    }
    
    for (size_t ch = 0; ch < movingMind.size(); ++ch)
    {
        std::string fname = outputPrefix + "_moving_mind_ch" + std::to_string(ch) + ".nrrd";
        writer->SetFileName(fname);
        writer->SetInput(movingMind[ch]);
        try { writer->Update(); std::cout << "    " << fname << std::endl; }
        catch (...) {}
    }
    
    std::cout << "\n=== SUCCESS ===" << std::endl;
    std::cout << "\nD_P Images (Patch Distance):" << std::endl;
    std::cout << "  - Should look like paper Fig. 1 (grayscale gradients)" << std::endl;
    std::cout << "  - Bright = small patch distance (similar regions)" << std::endl;
    std::cout << "  - Dark = large patch distance (different regions)" << std::endl;
    std::cout << "  - If it looks like binary edges → PROBLEM!\n" << std::endl;
    
    std::cout << "MIND Features:" << std::endl;
    std::cout << "  - Inverted from D_P: Bright = high similarity" << std::endl;
    std::cout << "  - Use D_P images for diagnosis\n" << std::endl;
    
    std::cout << "Next Steps:" << std::endl;
    std::cout << "1. Load D_P images in Slicer" << std::endl;
    std::cout << "2. Check if they show gradual grayscale transitions" << std::endl;
    std::cout << "3. Compare with paper Fig. 1 visual style" << std::endl;
    std::cout << "4. If moving D_P is mostly black → use thicker volume\n" << std::endl;
    
    return EXIT_SUCCESS;
}
