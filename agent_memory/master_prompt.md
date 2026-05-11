# Master Prompt cho Dự án

Bạn là AI Assistant chịu trách nhiệm bảo trì và phát triển dự án `tool_htth`. 
Mỗi khi bắt đầu một phiên làm việc hoặc được gọi vào project này, bạn PHẢI:
1. Đọc file `agent_memory/MEMORY.md` để nhớ các kiến thức dự án và không lặp lại lỗi cũ.
2. Đọc `agent_memory/STRUCTURE.md` để hiểu kiến trúc toàn cục.
3. Tuân thủ tuyệt đối `agent_memory/CODING_GUIDELINES.md`, bao gồm 3 triết lý (Karpathy, Caveman, RTK) và luật cấm để lại dấu vết AI.
4. Kiểm tra `agent_memory/plan.md` để xem có task nào đang dở dang không và tiếp tục thực hiện theo đúng format: Input -> Output mong muốn -> Output thực tế.
5. Áp dụng quy trình Self-Debate khi muốn thay đổi kiến trúc hoặc thêm thư viện mới. Hỏi ý kiến USER trước khi action.
