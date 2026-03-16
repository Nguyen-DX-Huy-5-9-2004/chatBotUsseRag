from typing import TypedDict, List, Dict, Any, Optional
from operator import add
from typing_extensions import Annotated

class MultiRoleAgentState(TypedDict):

    user_input: str          
    session_id: str
    conversation_history: str

    # Prompt gốc của vai trò
    base_prompt: str   
    tools: Optional[List[str]] 
    full_prompt: str

    # Phân tích từ Gemini Analyzer
    llm_analysis: Optional[str]      
    required_tools: Optional[List[Dict[str, Any]]] 
    
    # Kết quả thực thi tool
    tool_results: Annotated[List[Dict[str, Any]], add]  

    # Câu trả lời tổng hợp
    final_answer: Optional[str]  
