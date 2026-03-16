import uuid
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent_core.state import MultiRoleAgentState
from agent_core.node import (
    user_input,
    role_manager,
    task_analyzer,
    tool_executor,
    llm_response,
)

class MultiRoleAgentGraph:
    def __init__(self):
   
        self.graph = StateGraph(MultiRoleAgentState)
        self.memory = MemorySaver()
        # Khai báo các node trên đồ thị xử lý
        self.graph.add_node("user_input", self._wrap_node(user_input))
        self.graph.add_node("role_manager", self._wrap_node(role_manager))
        self.graph.add_node("task_analyzer", self._wrap_node(task_analyzer))
        self.graph.add_node("tool_executor", self._wrap_node(tool_executor))
        self.graph.add_node("llm_response", self._wrap_node(llm_response))

        # Định nghĩa các cạnh để nối chuỗi node
        self.graph.set_entry_point("user_input")
        self.graph.add_edge("user_input", "role_manager")
        self.graph.add_edge("role_manager", "task_analyzer")
        self.graph.add_edge("task_analyzer", "tool_executor")
        self.graph.add_edge("tool_executor", "llm_response")
        self.graph.add_edge("llm_response", END)

        # Biên dịch và lưu checkpoint cho graph
        self.app = self.graph.compile(checkpointer=self.memory)

    # Các helper để trả về state theo yêu cầu của LangGraph
    def _wrap_node(self, func):
        """
        LangGraph yêu cầu node nhận state và trả về state.
        Trong khi node của ta chỉ cập nhật state trực tiếp (in-place),
        nên cần bọc lại để trả về state sau khi cập nhật.
        """
        def wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
            func(state)
            return state
        return wrapped


    def create_new_state(self, user_question: str,session_id: str) -> MultiRoleAgentState:
        """
        Mỗi lần người dùng hỏi, tạo một state hoàn toàn mới,
        tránh dùng lại dữ liệu cũ trong bộ nhớ LangGraph.
        """
        return {
            "user_input": user_question,
            "session_id": session_id,
            "conversation_history": "",
            "base_prompt": None,
            "tools": None,
            "llm_analysis": None,
            "required_tools": [],
            "tool_results": [],
            "final_answer": None,
        }

    # Triển khai đồ thị cho mỗi lượt chat
    def run(self, state: MultiRoleAgentState) -> Dict[str, Any]:
        """
        Nhận vào 1 state (dict) và trả ra state cuối cùng sau khi chạy qua graph.
        """
        # Cấp thread_id mới để không ghi đè checkpoint cũ
        thread_id = str(uuid.uuid4())

        final_state = self.app.invoke(
            state,
            config={"configurable": {"thread_id": thread_id}},
        )

        return final_state
