"""
Registration Evaluation 模块初始化文件
用于评估配准结果，包括 TRE（目标配准误差）和 Mattes MI（互信息）
"""
from .registration_evaluation_widget import RegistrationEvaluationWidget
from .registration_evaluation_logic import RegistrationEvaluationLogic

__all__ = ['RegistrationEvaluationWidget', 'RegistrationEvaluationLogic']
