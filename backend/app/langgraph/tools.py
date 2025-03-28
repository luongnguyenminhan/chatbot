from langchain_core.tools import tool
import requests
import json
from typing import Optional

@tool(return_direct=True)
def conversation_history_summary():
    """Summarize the conversation history to demonstrate persistent memory capability."""
    print("\n[TOOLS] conversation_history_summary called")
    return "I can access our complete conversation history because I'm using the MemorySaver checkpointer. This allows me to maintain context across multiple exchanges in this conversation thread."

def get_user_subcategories(user_id):
    """Fetch subcategories for a given user ID from the API."""
    print(f"\n[TOOLS] get_user_subcategories called for user: {user_id}")
    headers = {"X-Webhook-Secret": "thisIsSerectKeyPythonService"}
    url = f"https://easymoney.anttravel.online/api/v1/user-spending-models/current/webhook/sub-categories?userId={user_id}"
    print(f"[TOOLS] Making API request to: {url}")
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(f"[TOOLS] API request successful, status code: {response.status_code}")
        subcategories = response.json().get("data", [])
        print(f"[TOOLS] Retrieved {len(subcategories)} subcategories")
        formatted_subcategories = []
        for sc in subcategories:
            formatted_subcategories.append(f"""
                                           Là một danh mục con nằm trong danh mục {sc.get("categoryName")}, danh mục này có tên là {sc.get("name")}, mã danh mục là {sc.get("code")}, mô tả là {sc.get("description")}.                                        
                                           """)
        return "\n".join(formatted_subcategories)
    else:
        print(f"[TOOLS] API request failed, status code: {response.status_code}")
        return None

@tool(return_direct=False)
def user_input_expense():#(user_id: Optional[str] = None):
    """Xác định số tiền chi tiêu và mục đích chi tiêu sau đó phân loại vào danh mục chi tiêu dựa trên danh sách nhận được từ API."""
    print(f"\n[TOOLS] user_input_expense called with user_id: {user_id}")
    # Fetch subcategories from the API
    user_id = "7F583FFD-4C32-44C8-6214-08DD3DDA7643"
    if user_id:
        try:
            print(f"[TOOLS] Fetching subcategories for user_id: {user_id}")
            headers = {"X-Webhook-Secret": "thisIsSerectKeyPythonService"}
            url = f"https://easymoney.anttravel.online/api/v1/user-spending-models/current/webhook/sub-categories?userId={user_id}"
            print(f"[TOOLS] Making API request to: {url}")
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                subcategories = response.json().get("data", [])
                print(f"[TOOLS] Retrieved {len(subcategories)} subcategories")
                
                # Format subcategories for the LLM to better understand and select from
                formatted_subcategories = []
                for sc in subcategories:
                    formatted_subcategories.append({
                        "name": sc.get("name"),
                        "description": sc.get("description"),
                        "category": sc.get("categoryName"),
                        "code": sc.get("code")
                    })
                
                print("[TOOLS] Successfully formatted subcategories for LLM")
                return {
                    "message": "Vui lòng cung cấp số tiền chi tiêu và mục đích chi tiêu. Tôi sẽ giúp phân loại vào danh mục phù hợp.",
                    "subcategories": formatted_subcategories
                }
            else:
                print(f"[TOOLS] API request failed, status code: {response.status_code}")
                return "Tôi gặp sự cố khi truy xuất danh mục chi tiêu. Vui lòng thử lại sau."
        except Exception as e:
            print(f"[TOOLS] Error occurred: {str(e)}")
            return f"Lỗi khi truy cập danh mục chi tiêu: {str(e)}"
    
    print("[TOOLS] No user_id provided")
    return "Vui lòng cung cấp số tiền chi tiêu và mục đích chi tiêu. Tôi sẽ giúp phân loại dựa trên các danh mục có sẵn."

tools = [user_input_expense]
