import customtkinter as ctk
import threading
import psutil
import datetime
from deku_ai_agent import process_query, USER_NAME, MISTRAL_MODEL, mistral_history

class DekuApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title(f"DEKU AI - {USER_NAME}'s Friend")
        self.geometry("900x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="DEKU v6", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=20)

        self.status_label = ctk.CTkLabel(self.sidebar, text="System Stats", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_label.pack(pady=(20, 10))

        self.cpu_label = ctk.CTkLabel(self.sidebar, text="CPU: 0%")
        self.cpu_label.pack()
        
        self.ram_label = ctk.CTkLabel(self.sidebar, text="RAM: 0%")
        self.ram_label.pack()

        self.model_label = ctk.CTkLabel(self.sidebar, text=f"Model: {MISTRAL_MODEL}", font=ctk.CTkFont(size=10), wraplength=150)
        self.model_label.pack(side="bottom", pady=20)

        # Chat Area
        self.chat_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(0, weight=1)

        self.chat_display = ctk.CTkTextbox(self.chat_frame, state="disabled", font=ctk.CTkFont(size=14))
        self.chat_display.grid(row=0, column=0, sticky="nsew")

        # Input Area
        self.input_frame = ctk.CTkFrame(self, corner_radius=10)
        self.input_frame.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.user_input = ctk.CTkEntry(self.input_frame, placeholder_text="Type your message here...", height=40)
        self.user_input.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.user_input.bind("<Return>", lambda e: self.send_message())

        self.send_button = ctk.CTkButton(self.input_frame, text="Send", command=self.send_message, width=100, height=40)
        self.send_button.grid(row=0, column=1, padx=10, pady=10)

        # Start background tasks
        self.update_stats()
        self.append_chat("DEKU", f"Yo {USER_NAME}! I'm online and ready to help. What's on your mind?")

    def update_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_label.configure(text=f"CPU: {cpu}%")
        self.ram_label.configure(text=f"RAM: {ram}%")
        self.after(2000, self.update_stats)

    def append_chat(self, sender, message):
        self.chat_display.configure(state="normal")
        timestamp = datetime.datetime.now().strftime("%H:%M")
        self.chat_display.insert("end", f"[{timestamp}] {sender}: {message}\n\n")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")

    def send_message(self):
        msg = self.user_input.get().strip()
        if not msg:
            return
        
        self.user_input.delete(0, "end")
        self.append_chat("You", msg)
        
        # Run AI processing in a separate thread to keep UI responsive
        threading.Thread(target=self.get_ai_response, args=(msg,), daemon=True).start()

    def get_ai_response(self, query):
        try:
            response = process_query(query)
            self.after(0, lambda: self.append_chat("DEKU", response))
        except Exception as e:
            self.after(0, lambda: self.append_chat("SYSTEM", f"Error: {str(e)}"))

if __name__ == "__main__":
    app = DekuApp()
    app.mainloop()
