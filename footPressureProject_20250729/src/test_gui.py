import tkinter as tk
from datetime import datetime

def test_basic_gui():
    """기본 GUI 동작 테스트"""
    print("=== 기본 GUI 테스트 시작 ===")
    
    try:
        root = tk.Tk()
        root.title("테스트 GUI")
        root.geometry("400x300")
        
        label = tk.Label(root, text="GUI 테스트가 성공했습니다!", font=("Arial", 16))
        label.pack(pady=50)
        
        def on_button_click():
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] 버튼이 클릭되었습니다!")
            label.config(text=f"버튼 클릭됨: {timestamp}")
        
        button = tk.Button(root, text="테스트 버튼", command=on_button_click, font=("Arial", 12), padx=20, pady=10)
        button.pack(pady=20)
        
        print("GUI 창을 시작합니다...")
        root.mainloop()
        print("GUI가 종료되었습니다.")
        
    except Exception as e:
        print(f"GUI 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_gui()