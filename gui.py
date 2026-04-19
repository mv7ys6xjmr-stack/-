import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog, simpledialog
import threading
from node import P2PNode
from datetime import datetime

class P2PMessengerGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        
        self.colors = {
            'bg_dark': '#1a0b2e',
            'bg_medium': '#2d1b4e',
            'bg_light': '#3d2b5e',
            'accent_primary': '#9b59b6',
            'accent_secondary': '#8e44ad',
            'accent_hover': '#a569bd',
            'accent_success': '#00c92b',
            'accent_danger': '#a569bd',
            'accent_warning': "#00c92b",
            'text_primary': '#e8e8e8',
            'text_secondary': '#b8b8b8',
            'text_accent': '#d4a5f0',
            'chat_bg': '#0f0520',
            'timestamp': '#a569bd',
            'group_bg': '#2d1b4e',
            'group_selected': '#9b59b6'
        }
        
        self.root.configure(bg=self.colors['bg_dark'])
        
        self.groups = {}  
        self.current_group = None
        self.current_private_chat = None
        self.available_peers = []  
        
        self.setup_ttk_style()
        self.node = None
        self.setup_connection_frame()
    
    def setup_ttk_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TNotebook', background=self.colors['bg_dark'])
        style.configure('TNotebook.Tab', 
                       background=self.colors['bg_medium'],
                       foreground=self.colors['text_primary'],
                       padding=[10, 5],
                       font=('Arial', 10, 'bold'))
        style.map('TNotebook.Tab',
                 background=[('selected', self.colors['accent_primary'])],
                 foreground=[('selected', 'white')])
        
        style.configure('TFrame', background=self.colors['bg_dark'])
        style.configure('TLabelframe', 
                       background=self.colors['bg_dark'],
                       foreground=self.colors['text_primary'])
        style.configure('TLabelframe.Label', 
                       background=self.colors['bg_dark'],
                       foreground=self.colors['text_accent'])
    
    def setup_connection_frame(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.connection_frame = tk.Frame(self.root, bg=self.colors['bg_dark'])
        self.connection_frame.pack(expand=True, fill='both')
        
        center_frame = tk.Frame(self.connection_frame, bg=self.colors['bg_dark'])
        center_frame.pack(expand=True)
        
        title_label = tk.Label(
            center_frame, 
            text="Хуессенджер", 
            font=('Arial', 32, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_dark']
        )
        title_label.pack(pady=20)
        
        subtitle_label = tk.Label(
            center_frame,
            text="",
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark'],
            font=('Arial', 11)
        )
        subtitle_label.pack(pady=(0, 40))
        
        card_frame = tk.Frame(
            center_frame, 
            bg=self.colors['bg_medium'],
            relief=tk.RAISED,
            bd=2
        )
        card_frame.pack(pady=10, padx=30, ipadx=20, ipady=20)
        
        user_frame = tk.Frame(card_frame, bg=self.colors['bg_medium'])
        user_frame.pack(pady=10)
        
        tk.Label(
            user_frame, 
            text="Имя пользователя:", 
            fg=self.colors['text_primary'], 
            bg=self.colors['bg_medium'], 
            font=('Arial', 11, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        self.username_entry = tk.Entry(
            card_frame, 
            width=30, 
            font=('Arial', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT
        )
        self.username_entry.pack(pady=5)
        self.username_entry.insert(0, "User")
        
        port_frame = tk.Frame(card_frame, bg=self.colors['bg_medium'])
        port_frame.pack(pady=10)
        
        tk.Label(
            port_frame, 
            text="Ваш порт:", 
            fg=self.colors['text_primary'], 
            bg=self.colors['bg_medium'], 
            font=('Arial', 11, 'bold')
        ).pack(side=tk.LEFT, padx=5)
        
        self.port_entry = tk.Entry(
            card_frame, 
            width=30, 
            font=('Arial', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT
        )
        self.port_entry.pack(pady=5)
        self.port_entry.insert(0, "5000")
        
        tk.Frame(card_frame, height=2, bg=self.colors['accent_primary']).pack(fill=tk.X, pady=10)
        
        tk.Label(
            card_frame, 
            text="Подключиться к пиру:", 
            fg=self.colors['text_secondary'], 
            bg=self.colors['bg_medium'], 
            font=('Arial', 10)
        ).pack()
        
        peer_frame = tk.Frame(card_frame, bg=self.colors['bg_medium'])
        peer_frame.pack(pady=5)
        
        tk.Label(peer_frame, text="IP:", fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=5)
        self.peer_ip_entry = tk.Entry(
            peer_frame, 
            width=15, 
            font=('Arial', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT
        )
        self.peer_ip_entry.pack(side=tk.LEFT, padx=5)
        self.peer_ip_entry.insert(0, "192.168.1.")
        
        tk.Label(peer_frame, text="Порт:", fg=self.colors['text_primary'], bg=self.colors['bg_medium']).pack(side=tk.LEFT, padx=5)
        
        self.peer_port_entry = tk.Entry(
            peer_frame, 
            width=10, 
            font=('Arial', 11),
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT
        )
        self.peer_port_entry.pack(side=tk.LEFT, padx=5)
        self.peer_port_entry.insert(0, "5001")
        
        btn_start = tk.Button(
            center_frame, 
            text="Запустить узел", 
            command=self.start_node,
            bg=self.colors['accent_primary'],
            fg='white',
            font=('Arial', 14, 'bold'),
            padx=30,
            pady=10,
            cursor='hand2',
            relief=tk.FLAT,
            activebackground=self.colors['accent_hover'],
            activeforeground='white'
        )
        btn_start.pack(pady=20)
        
        btn_connect = tk.Button(
            center_frame,
            text="Подключиться к пиру",
            command=self.connect_to_peer,
            bg=self.colors['accent_secondary'],
            fg='white',
            font=('Arial', 11),
            padx=20,
            pady=5,
            cursor='hand2',
            relief=tk.FLAT,
            activebackground=self.colors['accent_hover']
        )
        btn_connect.pack(pady=5)
    
    def start_node(self):
        try:
            port = int(self.port_entry.get())
            username = self.username_entry.get()
            
            if not username.strip():
                messagebox.showerror("Ошибка", "Введите имя пользователя")
                return
            
            self.node = P2PNode('0.0.0.0', port, username)
            self.node.message_callback = self.on_message_received
            
            self.groups = {}
            
            node_thread = threading.Thread(target=self.node.start, daemon=True)
            node_thread.start()
            
            self.setup_main_interface()
            
        except ValueError:
            messagebox.showerror("Ошибка", "Порт должен быть числом")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось запустить узел: {e}")
    
    def connect_to_peer(self):
        if self.node:
            ip = self.peer_ip_entry.get()
            try:
                port = int(self.peer_port_entry.get())
                if self.node.connect_to_peer(ip, port):
                    messagebox.showinfo("Успех", f"Подключен к {ip}:{port}")
                    self.refresh_peers_list()
                else:
                    messagebox.showwarning("Ошибка", f"Не удалось подключиться к {ip}:{port}")
            except ValueError:
                messagebox.showerror("Ошибка", "Порт должен быть числом")
    
    def setup_main_interface(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        
        info_frame = tk.Frame(self.root, bg=self.colors['bg_medium'], height=70)
        info_frame.pack(fill=tk.X)
        
        status_frame = tk.Frame(info_frame, bg=self.colors['bg_medium'])
        status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.status_label = tk.Label(
            status_frame,
            text=f"{self.node.username} | Порт: {self.node.port} | IP: {self.node.local_ip}",
            fg=self.colors['text_accent'],
            bg=self.colors['bg_medium'],
            font=('Arial', 10, 'bold')
        )
        self.status_label.pack(side=tk.LEFT, pady=20, padx=20)
        
        exit_frame = tk.Frame(info_frame, bg=self.colors['bg_medium'])
        exit_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        exit_btn = tk.Button(
            exit_frame,
            text="Выход",
            command=self.exit_app,
            bg=self.colors['accent_danger'],
            fg='white',
            font=('Arial', 11, 'bold'),
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=8,
            activebackground="#ffffff"
        )
        exit_btn.pack(pady=18, padx=20)
        
        main_container = tk.Frame(self.root, bg=self.colors['bg_dark'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_panel = tk.Frame(main_container, bg=self.colors['bg_medium'], width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        groups_header = tk.Label(
            left_panel,
            text="ГРУППЫ",
            font=('Arial', 12, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_medium']
        )
        groups_header.pack(pady=(10, 5))
        
        self.groups_listbox = tk.Listbox(
            left_panel,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['accent_primary'],
            selectforeground='white',
            font=('Arial', 10),
            height=8,
            relief=tk.FLAT
        )
        self.groups_listbox.pack(fill=tk.X, padx=10, pady=5)
        self.groups_listbox.bind('<<ListboxSelect>>', self.on_group_select)
        
        create_group_btn = tk.Button(
            left_panel,
            text="+ Создать группу",
            command=self.create_group_dialog,
            bg=self.colors['accent_secondary'],
            fg='white',
            font=('Arial', 10),
            cursor='hand2',
            relief=tk.FLAT,
            pady=5
        )
        create_group_btn.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Frame(left_panel, height=2, bg=self.colors['accent_primary']).pack(fill=tk.X, padx=10, pady=10)
        
        private_header = tk.Label(
            left_panel,
            text="ЛИЧНЫЕ ЧАТЫ",
            font=('Arial', 12, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_medium']
        )
        private_header.pack(pady=(10, 5))
        
        self.peers_listbox = tk.Listbox(
            left_panel,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['accent_secondary'],
            selectforeground='white',
            font=('Arial', 10),
            height=8,
            relief=tk.FLAT
        )
        self.peers_listbox.pack(fill=tk.X, padx=10, pady=5)
        self.peers_listbox.bind('<<ListboxSelect>>', self.on_peer_select)
        
        right_panel = tk.Frame(main_container, bg=self.colors['bg_dark'])
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.chat_header = tk.Label(
            right_panel,
            text="Выберите чат",
            font=('Arial', 12, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_medium'],
            pady=10
        )
        self.chat_header.pack(fill=tk.X)
        self.chat_area = scrolledtext.ScrolledText(
            right_panel,
            wrap=tk.WORD,
            bg=self.colors['chat_bg'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 11),
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT,
            bd=0,
            height=20
        )
        self.chat_area.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.chat_area.tag_config('my_message', 
                                  foreground=self.colors['text_accent'],
                                  font=('Segoe UI', 11, 'bold'))
        self.chat_area.tag_config('their_message', 
                                  foreground=self.colors['text_primary'])
        self.chat_area.tag_config('timestamp', 
                                  foreground=self.colors['timestamp'],
                                  font=('Segoe UI', 9))
        self.chat_area.tag_config('system', 
                                  foreground=self.colors['accent_warning'],
                                  font=('Segoe UI', 10, 'italic'))
        
        self.members_panel = tk.Frame(right_panel, bg=self.colors['bg_medium'], width=200)
        self.members_label = tk.Label(
            self.members_panel,
            text="Участники",
            font=('Arial', 10, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_medium']
        )
        self.members_label.pack(pady=5)
        
        self.members_listbox = tk.Listbox(
            self.members_panel,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            font=('Arial', 9),
            height=10,
            relief=tk.FLAT
        )
        self.members_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.group_buttons_frame = tk.Frame(self.members_panel, bg=self.colors['bg_medium'])
        self.invite_btn = tk.Button(
            self.group_buttons_frame,
            text="Пригласить",
            command=self.invite_to_group,
            bg=self.colors['accent_success'],
            fg='white',
            font=('Arial', 9),
            cursor='hand2',
            relief=tk.FLAT
        )
        self.invite_btn.pack(side=tk.LEFT, padx=5)
        
        self.leave_btn = tk.Button(
            self.group_buttons_frame,
            text="Выйти",
            command=self.leave_group,
            bg=self.colors['accent_danger'],
            fg='white',
            font=('Arial', 9),
            cursor='hand2',
            relief=tk.FLAT
        )
        self.leave_btn.pack(side=tk.LEFT, padx=5)
        
        input_frame = tk.Frame(right_panel, bg=self.colors['bg_dark'])
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.message_entry = tk.Entry(
            input_frame,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            font=('Segoe UI', 11),
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT,
            bd=0
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)
        self.message_entry.bind('<Return>', lambda e: self.send_current_message())
        
        attach_btn = tk.Button(
            input_frame,
            text="📎",
            command=self.send_file_dialog,
            bg=self.colors['bg_light'],
            fg=self.colors['text_secondary'],
            font=('Arial', 12),
            bd=0,
            cursor='hand2'
        )
        attach_btn.pack(side=tk.RIGHT, padx=5)
        
        send_btn = tk.Button(
            input_frame,
            text="Отправить",
            command=self.send_current_message,
            bg=self.colors['accent_primary'],
            fg='white',
            font=('Arial', 10, 'bold'),
            bd=0,
            cursor='hand2',
            padx=15,
            pady=5
        )
        send_btn.pack(side=tk.RIGHT)
        
        self.bottom_notebook = ttk.Notebook(self.root)
        self.bottom_notebook.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.history_frame = tk.Frame(self.bottom_notebook, bg=self.colors['bg_dark'])
        self.bottom_notebook.add(self.history_frame, text="История")
        self.setup_history_tab()
        
        self.info_frame = tk.Frame(self.bottom_notebook, bg=self.colors['bg_dark'])
        self.bottom_notebook.add(self.info_frame, text="Информация")
        self.setup_info_tab()
        
        self.refresh_groups_list()
        self.refresh_peers_list()
        self.update_status()
    
    def refresh_groups_list(self):
        self.groups_listbox.delete(0, tk.END)
        for group_id, group in self.groups.items():
            display_text = f"{group['name']} ({len(group['members'])})"
            self.groups_listbox.insert(tk.END, display_text)
    
    def refresh_peers_list(self):
        self.peers_listbox.delete(0, tk.END)
        self.available_peers = []
        
        if self.node:
            for peer_host, peer_port in self.node.peers:
                peer_name = f"Пир {peer_port}"
                self.peers_listbox.insert(tk.END, peer_name)
                self.available_peers.append({'name': peer_name, 'ip': peer_host, 'port': peer_port})
    
    def on_group_select(self, event):
        selection = self.groups_listbox.curselection()
        if selection:
            index = selection[0]
            group_id = list(self.groups.keys())[index]
            self.current_group = group_id
            self.current_private_chat = None
            
            group = self.groups[group_id]
            self.chat_header.config(text=f"Группа: {group['name']}")
            
            self.members_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
            self.group_buttons_frame.pack(fill=tk.X, pady=5)
            
            self.members_listbox.delete(0, tk.END)
            for member in group['members']:
                if member == group['admin']:
                    self.members_listbox.insert(tk.END, f"{member} (админ)")
                else:
                    self.members_listbox.insert(tk.END, f"{member}")
            
            self.load_group_messages(group_id)
    
    def on_peer_select(self, event):
        selection = self.peers_listbox.curselection()
        if selection:
            self.current_private_chat = selection[0]
            self.current_group = None
            
            self.members_panel.pack_forget()
            
            peer_name = self.peers_listbox.get(selection[0])
            self.chat_header.config(text=f"Личный чат: {peer_name}")
            
            self.chat_area.delete(1.0, tk.END)
            self.chat_area.insert(tk.END, f"Личный чат с {peer_name}\n", 'system')
            self.chat_area.insert(tk.END, "-" * 50 + "\n", 'system')
    
    def load_group_messages(self, group_id):
        self.chat_area.delete(1.0, tk.END)
        group = self.groups[group_id]
        
        if group['messages']:
            for msg in group['messages']:
                sender_tag = 'my_message' if msg['sender'] == self.node.username else 'their_message'
                self.chat_area.insert(tk.END, f"[{msg['timestamp']}] ", 'timestamp')
                self.chat_area.insert(tk.END, f"{msg['sender']}: ", sender_tag)
                self.chat_area.insert(tk.END, f"{msg['content']}\n", 'their_message')
        else:
            self.chat_area.insert(tk.END, f"Добро пожаловать в группу {group['name']}!\n", 'system')
            self.chat_area.insert(tk.END, "-" * 50 + "\n", 'system')
        
        self.chat_area.see(tk.END)
    
    def send_current_message(self):
        message = self.message_entry.get().strip()
        if not message:
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if self.current_group:
            group = self.groups[self.current_group]
            msg_data = {
                'sender': self.node.username,
                'content': message,
                'timestamp': timestamp
            }
            group['messages'].append(msg_data)
            
            self.chat_area.insert(tk.END, f"[{timestamp}] ", 'timestamp')
            self.chat_area.insert(tk.END, f"Вы: ", 'my_message')
            self.chat_area.insert(tk.END, f"{message}\n", 'their_message')
            self.chat_area.see(tk.END)
            
        elif self.current_private_chat is not None:
            self.chat_area.insert(tk.END, f"[{timestamp}] ", 'timestamp')
            self.chat_area.insert(tk.END, f"Вы: ", 'my_message')
            self.chat_area.insert(tk.END, f"{message}\n", 'their_message')
            self.chat_area.see(tk.END)
        
        self.message_entry.delete(0, tk.END)
    
    def create_group_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Создать группу")
        dialog.geometry("500x450")
        dialog.configure(bg=self.colors['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Создание новой группы",
            font=('Arial', 14, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_dark']
        ).pack(pady=10)
        
        tk.Label(
            dialog,
            text="Название группы:",
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        ).pack(pady=5)
        
        name_entry = tk.Entry(
            dialog,
            width=30,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_accent'],
            relief=tk.FLAT,
            font=('Arial', 11)
        )
        name_entry.pack(pady=5)
        
        tk.Label(
            dialog,
            text="Выберите участников (можно несколько):",
            fg=self.colors['text_primary'],
            bg=self.colors['bg_dark']
        ).pack(pady=(15, 5))
        
        members_frame = tk.Frame(dialog, bg=self.colors['bg_medium'])
        members_frame.pack(pady=5, padx=20, fill=tk.BOTH, expand=True)
        
        members_listbox = tk.Listbox(
            members_frame,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['accent_primary'],
            selectforeground='white',
            font=('Arial', 10),
            height=8,
            relief=tk.FLAT,
            selectmode=tk.MULTIPLE
        )
        members_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        members_listbox.insert(tk.END, self.node.username)  
        
        for peer in self.available_peers:
            if peer['name'] != self.node.username:
                members_listbox.insert(tk.END, peer['name'])
        
        tk.Label(
            dialog,
            text="(Для выбора нескольких зажмите Ctrl или Shift)",
            fg=self.colors['text_secondary'],
            bg=self.colors['bg_dark'],
            font=('Arial', 9)
        ).pack(pady=5)
        
        btn_frame = tk.Frame(dialog, bg=self.colors['bg_dark'])
        btn_frame.pack(pady=20)
        
        def do_create():
            group_name = name_entry.get()
            if not group_name:
                messagebox.showwarning("Внимание", "Введите название группы")
                return
            
            selected_indices = members_listbox.curselection()
            selected_members = [members_listbox.get(i) for i in selected_indices]
            
            if not selected_members:
                selected_members = [self.node.username]
            
            group_id = f"group_{len(self.groups) + 1}_{int(datetime.now().timestamp())}"
            self.groups[group_id] = {
                'name': group_name,
                'members': selected_members,
                'messages': [],
                'admin': self.node.username
            }
            
            self.refresh_groups_list()
            dialog.destroy()
            messagebox.showinfo("Успех", f"Группа '{group_name}' создана!\nУчастники: {', '.join(selected_members)}")
        
        tk.Button(
            btn_frame,
            text="Создать",
            command=do_create,
            bg=self.colors['accent_primary'],
            fg='white',
            font=('Arial', 11, 'bold'),
            cursor='hand2',
            relief=tk.FLAT,
            padx=25,
            pady=5
        ).pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            btn_frame,
            text="Отмена",
            command=dialog.destroy,
            bg=self.colors['accent_danger'],
            fg='white',
            font=('Arial', 11),
            cursor='hand2',
            relief=tk.FLAT,
            padx=25,
            pady=5
        ).pack(side=tk.LEFT, padx=10)
    
    def invite_to_group(self):
        if not self.current_group:
            return
        
        if not self.available_peers:
            messagebox.showwarning("Внимание", "Нет доступных пиров для приглашения")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Пригласить в группу")
        dialog.geometry("350x300")
        dialog.configure(bg=self.colors['bg_dark'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Выберите пользователя:",
            font=('Arial', 12, 'bold'),
            fg=self.colors['text_accent'],
            bg=self.colors['bg_dark']
        ).pack(pady=10)
        
        user_listbox = tk.Listbox(
            dialog,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            selectbackground=self.colors['accent_primary'],
            selectforeground='white',
            font=('Arial', 10),
            height=10,
            relief=tk.FLAT
        )
        user_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        current_members = self.groups[self.current_group]['members']
        for peer in self.available_peers:
            if peer['name'] not in current_members and peer['name'] != self.node.username:
                user_listbox.insert(tk.END, peer['name'])
        
        if user_listbox.size() == 0:
            tk.Label(
                dialog,
                text="Нет доступных пользователей для приглашения",
                fg=self.colors['accent_warning'],
                bg=self.colors['bg_dark']
            ).pack(pady=20)
        
        def do_invite():
            selection = user_listbox.curselection()
            if selection:
                username = user_listbox.get(selection[0])
                self.groups[self.current_group]['members'].append(username)
                
                self.members_listbox.insert(tk.END, f"👤 {username}")
                dialog.destroy()
                messagebox.showinfo("Успех", f"{username} приглашён в группу!")
        
        tk.Button(
            dialog,
            text="Пригласить",
            command=do_invite,
            bg=self.colors['accent_success'],
            fg='white',
            font=('Arial', 11),
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=5
        ).pack(pady=10)
    
    def leave_group(self):
        if not self.current_group:
            return
        
        if messagebox.askyesno("Выйти из группы", "Вы уверены, что хотите покинуть группу?"):
            group = self.groups[self.current_group]
            if self.node.username in group['members']:
                group['members'].remove(self.node.username)
                
                if not group['members']:
                    del self.groups[self.current_group]
                else:
                    if group['admin'] == self.node.username and group['members']:
                        group['admin'] = group['members'][0]
                
                self.current_group = None
                self.refresh_groups_list()
                self.chat_header.config(text="Выберите чат")
                self.members_panel.pack_forget()
                self.chat_area.delete(1.0, tk.END)
                messagebox.showinfo("Успех", "Вы покинули группу")
    
    def send_file_dialog(self):
        if not self.node:
            messagebox.showerror("Ошибка", "Узел не запущен")
            return
        
        filepath = filedialog.askopenfilename(title="Выберите файл для отправки")
        if not filepath:
            return
        
        if self.current_group:
            import os
            filename = os.path.basename(filepath)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            self.chat_area.insert(tk.END, f"[{timestamp}] ", 'timestamp')
            self.chat_area.insert(tk.END, f"Вы: ", 'my_message')
            self.chat_area.insert(tk.END, f"[Файл] {filename}\n", 'system')
            self.chat_area.see(tk.END)
            
            messagebox.showinfo("Файл", f"Файл {filename} отправлен в группу!")
        else:
            recipient_window = tk.Toplevel(self.root)
            recipient_window.title("Отправить файл")
            recipient_window.geometry("400x250")
            recipient_window.configure(bg=self.colors['bg_dark'])
            recipient_window.transient(self.root)
            recipient_window.grab_set()
            
            tk.Label(
                recipient_window,
                text="Отправка файла",
                font=('Arial', 14, 'bold'),
                fg=self.colors['text_accent'],
                bg=self.colors['bg_dark']
            ).pack(pady=10)
            
            import os
            filename = os.path.basename(filepath)
            tk.Label(
                recipient_window,
                text=f"Файл: {filename}",
                fg=self.colors['text_primary'],
                bg=self.colors['bg_dark']
            ).pack(pady=5)
            
            tk.Label(
                recipient_window,
                text="IP получателя:",
                fg=self.colors['text_primary'],
                bg=self.colors['bg_dark']
            ).pack(pady=5)
            
            ip_entry = tk.Entry(recipient_window, width=30, bg=self.colors['bg_light'],
                                fg=self.colors['text_primary'])
            ip_entry.pack(pady=5)
            ip_entry.insert(0, "192.168.1.")
            
            tk.Label(
                recipient_window,
                text="Порт:",
                fg=self.colors['text_primary'],
                bg=self.colors['bg_dark']
            ).pack(pady=5)
            
            port_entry = tk.Entry(recipient_window, width=10, bg=self.colors['bg_light'],
                                  fg=self.colors['text_primary'])
            port_entry.pack(pady=5)
            port_entry.insert(0, "5001")
            
            def do_send():
                try:
                    ip = ip_entry.get()
                    port = int(port_entry.get())
                    recipient_window.destroy()
                    
                    success, msg = self.node.send_file_to_peer(filepath, ip, port)
                    if success:
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        self.chat_area.insert(tk.END, f"[{timestamp}] ", 'timestamp')
                        self.chat_area.insert(tk.END, f"Вы: ", 'my_message')
                        self.chat_area.insert(tk.END, f"[Файл] {filename}\n", 'system')
                        self.chat_area.see(tk.END)
                        messagebox.showinfo("Успех", msg)
                    else:
                        messagebox.showerror("Ошибка", msg)
                except ValueError:
                    messagebox.showerror("Ошибка", "Порт должен быть числом")
            
            tk.Button(
                recipient_window,
                text="Отправить",
                command=do_send,
                bg=self.colors['accent_primary'],
                fg='white',
                font=('Arial', 11),
                cursor='hand2',
                relief=tk.FLAT,
                padx=20,
                pady=5
            ).pack(pady=20)
    
    def setup_history_tab(self):
        search_frame = tk.Frame(self.history_frame, bg=self.colors['bg_dark'])
        search_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.search_entry = tk.Entry(
            search_frame, 
            width=40,
            bg=self.colors['bg_light'],
            fg=self.colors['text_primary'],
            relief=tk.FLAT
        )
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<Return>', lambda e: self.search_history())
        
        tk.Button(
            search_frame, 
            text="Найти",
            command=self.search_history,
            bg=self.colors['accent_primary'],
            fg='white',
            font=('Arial', 10),
            cursor='hand2',
            relief=tk.FLAT,
            padx=15,
            pady=5
        ).pack(side=tk.LEFT, padx=5)
        
        self.history_area = scrolledtext.ScrolledText(
            self.history_frame, 
            height=10, 
            bg=self.colors['chat_bg'], 
            fg=self.colors['text_primary'],
            relief=tk.FLAT
        )
        self.history_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    def setup_info_tab(self):
        self.info_text = scrolledtext.ScrolledText(
            self.info_frame, 
            height=10, 
            bg=self.colors['chat_bg'], 
            fg=self.colors['text_accent'],
            font=('Courier', 10),
            relief=tk.FLAT
        )
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Button(
            self.info_frame, 
            text="Обновить", 
            command=self.refresh_info, 
            bg=self.colors['accent_secondary'], 
            fg='white',
            cursor='hand2',
            relief=tk.FLAT,
            padx=20,
            pady=5
        ).pack(pady=5)
        
        self.refresh_info()
    
    def on_message_received(self, message):
        def update_chat():
            if self.current_private_chat is not None:
                self.chat_area.insert(tk.END, f"[{message.timestamp}] ", 'timestamp')
                self.chat_area.insert(tk.END, f"{message.sender}: ", 'their_message')
                self.chat_area.insert(tk.END, f"{message.content}\n", 'their_message')
                self.chat_area.see(tk.END)
        
        self.root.after(0, update_chat)
    
    def search_history(self):
        keyword = self.search_entry.get()
        if not keyword:
            messagebox.showwarning("Внимание", "Введите поисковый запрос")
            return
        
        results = []
        for group_id, group in self.groups.items():
            for msg in group['messages']:
                if keyword.lower() in msg['content'].lower():
                    results.append(f"[Группа {group['name']}] [{msg['timestamp']}] {msg['sender']}: {msg['content']}")
        
        self.history_area.delete(1.0, tk.END)
        if results:
            self.history_area.insert(tk.END, f"Результаты поиска по '{keyword}':\n\n")
            for res in results:
                self.history_area.insert(tk.END, f"{res}\n")
        else:
            self.history_area.insert(tk.END, "Ничего не найдено")
    
    def refresh_info(self):
        if self.node:
            info = self.node.show_routing_table()
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info)
    
    def update_status(self):
        if self.node and hasattr(self, 'status_label'):
            try:
                peers_count = len(self.node.peers)
                groups_count = len(self.groups)
                self.status_label.config(
                    text=f"{self.node.username} | Порт: {self.node.port} | IP: {self.node.local_ip} | Пиров: {peers_count} | Групп: {groups_count}"
                )
                self.refresh_peers_list()
            except:
                pass
        self.root.after(2000, self.update_status)
    
    def exit_app(self):
        if self.node:
            self.node.stop()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = P2PMessengerGUI()
    app.run()
