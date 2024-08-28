import json
from ossapi import Ossapi
import numpy as np
from math import log, log2, floor, ceil
import tkinter as tk
import customtkinter as ctk
from PIL import Image
import webbrowser
import threading
from os.path import exists

###GUI

#master functions
def execute():
    global script_terminating
    global counter
    global lobby_input_boxes
    script_terminating = False
    counter = 0

    disable_widgets(root) #disable everything, enable the terminate button
    try:
        #gather api inputs
        client_id = int(client_ID_input_box.get())
        client_secret = str(client_secret_input_box.get()).strip()

        #gather inputs from all non-empty mp text boxes as a list
        mp_str = [textbox.get() for textbox in lobby_input_boxes if textbox.get().strip()] #ignore empty boxes (boxes where 'strip()' is falsy)
        mp = [int(x) for x in mp_str]  # Convert input to int

        #fetch rounds
        number_of_qualifing_players = int(rounds_input_box.get())

        #check if input is valid
        if not 3<number_of_qualifing_players<129:
            raise ValueError('unsupported number of players') 

        #fetch number of redemption players
        redemption_players = redemption_inputbox.get()

        if redemption_players.isdigit():
            redemption_players = int(redemption_players)

            #check if input is valid
            if not 3<redemption_players<129:
                raise ValueError('unsupported number of redemption players') 

        else: #set to zero if empty
            redemption_players = 0

        #fetch boolean values
        double_elimination = not single_elimination_var.get()
        teams_vs = team_vs_var.get()
        manual_input = manual_scores_input_var.get()

        #create teams dictionary
        teams_dict = {}
        if teams_vs:
            input_teams = team_vs_input_box.get("1.0", tk.END).split('\n')

            #remove empty lines
            input_teams = [x for x in input_teams if x != '']

            #splits players into [name, team, id] (make nested list)
            input_teams = [x.split(',') for x in input_teams]

            #make keys of all teams
            for player in input_teams:
                if player[1] not in input_teams:
                    teams_dict[player[1]] = []
            
            #add players to teams
            for player in input_teams:
                teams_dict[player[1]].append(int(player[2]))
        
        #get seeding method
        seeding_method = seeding_method_menu.get()

        #execute script in a secondary thread to prevent lag in GUI
        script_thread = threading.Thread(target=create_bracket, args=(Ossapi(client_id, client_secret), mp, number_of_qualifing_players, redemption_players, double_elimination, seeding_method, manual_input, teams_vs, teams_dict))
        script_thread.start()

    except Exception as e:
        #print error and enable widgets if something is not in order
        GUI_terminal_print('error: '+str(e))
        enable_widgets(root)

def on_closing():
    global lobby_input_boxes

    #remember setup
    if remember_var.get():

        #delete lobbies with ghost text
        lobby_input_boxes = [x for x in lobby_input_boxes if x.get()!='']

        #organize data
        ínitial_data = {
            'Client_id': client_ID_input_box.get(),
            'Client_secret': client_secret_input_box.get(),
            'Rounds': rounds_input_box.get()
        }

        lobby_data = {}
        i = 0
        for lobby in lobby_input_boxes:
            i += 1
            lobby_data[f'Lobby{i}'] = lobby.get()
        
        bool_data = {
            'Single_Elimination': single_elimination_var.get(),
            '3rd_place': match_for_3rd_place_var.get(),
            'Redemption': redemption_inputbox.get(),
            'Manual': manual_scores_input_var.get(),
            'TeamVS': team_vs_var.get(),
            'Remember': remember_var.get()
        }

        teams_data = team_vs_input_box.get("1.0", tk.END)[:-1] #remove the newline character in the end to stop them from accumulating

        seed_method_data = seeding_method_menu.get()

        #write data
        with open('CFGs/configuration.cfg', 'w') as file:
            for key, val in ínitial_data.items():
                file.write(f'{key} = {val}\n')
            
            for key, val in lobby_data.items():
                file.write(f'{key} = {val}\n')
            
            for key, val in bool_data.items():
                file.write(f'{key} = {val}\n')
            
            file.write(f"Seed_method = {seed_method_data.replace(' ', '_')}\n")
            
            try:
                file.write(f'Teams_list =\n{teams_data}')

            except:
                #make it clear team list does not work if illigal characters are used
                file.write('Teams_list =\nteams list corrupt')

    #write standard blank cfg file
    else:
        with open('CFGs/configuration.cfg', 'w') as file:
            file.write('Client_id = \nClient_secret = \nRounds = \nSingle_Elimination = False\n3rd_place = False\nRedemption = \nManual = False\nTeamVS = False\nRemember = True\nSeed_method = Total_Score\nTeams_list =')
    
    #close window
    outer_root.destroy()

#error solver
def on_closing_error_solver(lobby: int, scores: dict, e_root: tk.Toplevel, e_remember_var: tk.BooleanVar):
    global failed_lobby_data
    outer_root.focus_set()

    #save scores to failed_lobby_data
    for player in scores:
        failed_lobby_data[player] = []
        for score in scores[player]:
            failed_lobby_data[player].append(int(score.get()))

    #save scores in CFG file
    if e_remember_var.get():
        with open(f'CFGs/fLobby{lobby}.cfg', 'w') as file:
            for key, val in failed_lobby_data.items():
                file.write(f'{key} = {", ".join(map(str, val))}\n')

    e_root.destroy()

def error_solver(api: Ossapi, lobby: int, mod_count: dict, teams_vs: bool, teams: dict):
    global failed_lobby_score_input_boxes
    global failed_lobby_player_list

    #read saved score or request new
    if exists(f'CFGs/fLobby{lobby}.cfg'):
        scores = {}
        with open(f'CFGs/fLobby{lobby}.cfg', 'r') as file:
            for line in file:
                key_str, value_str = line.strip().split(" = ")
                value_list = [int(x.strip()) for x in value_str.split(", ")]
                if teams_vs:
                    scores[key_str] = value_list
                else:
                    scores[int(key_str)] = value_list

    else:
        if teams_vs:
            scores = request_scores_teams(api, lobby, teams)
        else:
            scores = request_scores(api, lobby)

    #count number of maps for later use
    map_count = 0
    for mod in mod_count.values():
        for map in range(mod):
            map_count += 1
    
    #get indexable list of players
    failed_lobby_player_list = []
    for player in scores:
        failed_lobby_player_list.append(player)

    #create window
    e_root = ctk.CTkToplevel(outer_root)
    e_root.title("Error Solver")

    #create frame for title
    title_frame = ctk.CTkFrame(e_root)
    title_frame.grid(row=0, column=0, columnspan=5, sticky='w')

    #create title
    title = ctk.CTkLabel(title_frame, text="An error has occured in lobby ", font=("TkDefaultFont", 22, "bold"))
    title.pack(side='left', padx=(GUI_xspacing, 0))

    #create clickable link
    hyperlink_font = ctk.CTkFont(family="TkDefaultFont", size=22, weight="bold", underline=True)
    lobby_link = ctk.CTkLabel(title_frame, text=f"{lobby}", font=hyperlink_font, text_color='blue')
    lobby_link.pack(side='left', padx=(0, GUI_xspacing))
    lobby_link.bind("<Button-1>", lambda event: webbrowser.open(f'https://osu.ppy.sh/community/matches/{lobby}'))
    #imply label is clickable
    lobby_link.bind("<Enter>", lambda event: event.widget.configure(cursor="hand2"))
    lobby_link.bind("<Leave>", lambda event: event.widget.configure(cursor=""))

    #write initial text
    init_label = ctk.CTkLabel(e_root, text="The script has requested the scores:")
    init_label.grid(row=1, column=0, columnspan=3, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #write rows of players
    player_labels = []
    if teams_vs:
        for index, player in enumerate(scores):
            player_label = ctk.CTkLabel(e_root, text=player)
            player_label.grid(row=3+index, column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')
            player_labels.append(player_label)
    else:     
        for index, player in enumerate(scores):
            player_label = ctk.CTkLabel(e_root, text=api.user(int(player)).username) #convert ID to username if not teamVS
            player_label.grid(row=3+index, column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')
            player_labels.append(player_label)

    #write mods and get map count
    coloumn_index = 0
    for mod in mod_count:
        map_index = 0
        for map in range(mod_count[mod]):
            coloumn_index += 1
            map_index += 1
            mod_label = ctk.CTkLabel(e_root, text=f'{mod}{map_index}')
            mod_label.grid(row=2, column=coloumn_index, padx=GUI_xspacing, pady=GUI_yspacing)

    #create input boxes
    failed_lobby_score_input_boxes = {}
    row_index = 2
    for player in scores:
        row_index += 1
        coloumn_index = 0
        failed_lobby_score_input_boxes[player] = []
        for inputbox in range(map_count):
            coloumn_index += 1
            input_box = ctk.CTkEntry(e_root, width=70, validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(7)), '%P'))
            input_box.grid(row=row_index, column=coloumn_index, padx=GUI_xspacing, pady=GUI_yspacing)
            failed_lobby_score_input_boxes[player].append(input_box)

    #write requested scores
    for player in scores:
        for score in range(map_count):
            textbox = failed_lobby_score_input_boxes[player][score]
            if score<len(scores[player]): #don't write scores if too many scores were set
                textbox.insert(tk.END, scores[player][score])

    #write guiding message
    message_label = ctk.CTkLabel(e_root, text="Edit any incorrect scores, and press submit")
    message_label.grid(row=number_of_rows(e_root), column=0, columnspan=5, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #set delete protocol
    e_root.protocol("WM_DELETE_WINDOW", lambda: on_closing_error_solver(lobby, failed_lobby_score_input_boxes, e_root, e_remember_var))

    #make submit button (just a close window button)
    close_error_solver_button = ctk.CTkButton(e_root, text="Submit", command=lambda: on_closing_error_solver(lobby, failed_lobby_score_input_boxes, e_root, e_remember_var))
    close_error_solver_button.grid(row=number_of_rows(e_root), column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')
    
    ##make submit button active upon enter press

    # Bind the Enter key to the function when the Toplevel is in focus
    e_root.bind("<Return>", lambda event: on_closing_error_solver(lobby, failed_lobby_score_input_boxes, e_root, e_remember_var))
    
    # Set focus on the Toplevel
    e_root.focus_set()

    # Optional: Unbind when the Toplevel window loses focus
    def on_focus_out(event):
        e_root.unbind("<Return>")

    def on_focus_in(event):
        e_root.bind("<Return>", lambda event: on_closing_error_solver(lobby, failed_lobby_score_input_boxes, e_root, e_remember_var))

    # Bind focus out event to unbind the Enter key
    e_root.bind("<FocusOut>", on_focus_out)
    e_root.bind("<FocusIn>", on_focus_in)
    
    ##

    #make remember checkbox
    e_remember_var = tk.BooleanVar()
    e_remember_var.set(True)
    e_remember_checkbox = ctk.CTkCheckBox(e_root, text="Remember", variable=e_remember_var)
    e_remember_checkbox.grid(row=number_of_rows(e_root), column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #start the GUI event loop, and wait until window is closed
    global failed_lobby_data
    failed_lobby_data = {}
    e_root.wait_window()

    return failed_lobby_data

#manual input
def add_player_manual_scores(m_root: tk.Toplevel, player_input_boxes: list, map_count: dict, team_vs: bool):
    global manual_score_input_boxes

    #make room
    move_widgets(m_root, 3+len(player_input_boxes), -1)

    #create textbox for input player ID / team name
    if team_vs:
        textbox = ctk.CTkEntry(m_root, width=200)
    else:
        textbox = ctk.CTkEntry(m_root, width=100, validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(7)), '%P'))
    textbox.grid(row=4+len(player_input_boxes), column=0, padx=(5, 40), pady=GUI_yspacing, sticky='w')
    player_input_boxes.append(textbox)

    #create textboxes for score input
    individual_scores = []
    for map in range(map_count):
        text_box = ctk.CTkEntry(m_root, width=70, validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(7)), '%P'))
        text_box.grid(row=3+len(player_input_boxes), column=map+1, padx=GUI_xspacing, pady=GUI_yspacing)
        individual_scores.append(text_box)
    manual_score_input_boxes.append(individual_scores)

def on_closing_manual_scores(m_root: tk.Toplevel, player_input_boxes: list, manual_score_input_boxes: list, m_remember_var: tk.BooleanVar, team_vs: bool):
    global scores_dict
    scores_dict = {}
    outer_root.focus_set()

    #get scores
    i = -1
    for player in player_input_boxes:
        i += 1
        if player.get()!='': #ignore empty input boxes

            #get player ID / team name
            if team_vs:
                id = player.get()[:-1]
            else:
                id = int(player.get())
            
            #get scores
            scores_dict[id] = []
            for score in manual_score_input_boxes[i]:
                input_score = score.get()
                if input_score=='':
                    scores_dict[id].append(0)
                else:
                    scores_dict[id].append(int(score.get()))

    #save lobby file
    if m_remember_var.get():
        with open('CFGs/mLobby.cfg', 'w') as file:
            for key, val in scores_dict.items():
                file.write(f'{key} = {", ".join(str(x) for x in val)}\n')
    
    m_root.destroy()

def manual_scores_input(mod_count: dict, team_vs: bool):
    global scores_dict
    global manual_player_input_boxes

    #count number of maps for later use
    map_count = 0
    for mod in mod_count.values():
        for map in range(mod):
            map_count += 1

    #create the main application window
    m_root = ctk.CTkToplevel(outer_root)
    m_root.title("Manual Score Input")

    #create title
    title = ctk.CTkLabel(m_root, text="Manual Input", font=("TkDefaultFont", 12, "bold"))
    title.grid(row=0, column=0, columnspan=5, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #write initial text
    if team_vs:
        init_label = ctk.CTkLabel(m_root, text="Write teamname in the text box to the left. Write the achieved scores of the team in the textboxes besides")
    else:
        init_label = ctk.CTkLabel(m_root, text="Write player ID in the text box to the left. Write the achieved scores of the player in the textboxes besides")
    init_label.grid(row=1, column=0, columnspan=12, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    manual_player_input_boxes = []

    #create add player button
    if team_vs:
        add_player_button = ctk.CTkButton(m_root, text="Add team", command=lambda: add_player_manual_scores(m_root, manual_player_input_boxes, map_count, team_vs))
    else:
        add_player_button = ctk.CTkButton(m_root, text="Add player", command=lambda: add_player_manual_scores(m_root, manual_player_input_boxes, map_count, team_vs))
    add_player_button.grid(row=number_of_rows(m_root), column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #write mods and get map count
    coloumn_index = 0
    for mod in mod_count:
        map_index = 0
        for map in range(mod_count[mod]):
            coloumn_index += 1
            map_index += 1
            mod_label = ctk.CTkLabel(m_root, text=f'{mod}{map_index}')
            mod_label.grid(row=3, column=coloumn_index, padx=GUI_xspacing, pady=GUI_yspacing)

    #set delete protocol
    m_root.protocol("WM_DELETE_WINDOW", lambda: on_closing_manual_scores(m_root, manual_player_input_boxes, manual_score_input_boxes, m_remember_var, team_vs))

    #make submit button (just a close window button)
    close_manual_input_button = ctk.CTkButton(m_root, text="Submit", command=lambda: on_closing_manual_scores(m_root, manual_player_input_boxes, manual_score_input_boxes, m_remember_var, team_vs))
    close_manual_input_button.grid(row=number_of_rows(m_root), column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #make remember checkbox
    m_remember_var = tk.BooleanVar()
    m_remember_var.set(True)
    m_remember_checkbox = ctk.CTkCheckBox(m_root, text="Remember", variable=m_remember_var)
    m_remember_checkbox.grid(row=number_of_rows(m_root), column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #write saved data or make one initial input slot
    if exists('CFGs/mLobby.cfg'):
        with open('CFGs/mLobby.cfg', 'r') as file:
            for line in file:

                #add line in GUI
                add_player_manual_scores(m_root, manual_player_input_boxes, map_count, team_vs)

                #read saved scores
                key_str, value_str = line.strip().split(" = ")
                value_list = [int(x.strip()) for x in value_str.split(", ")]
                if team_vs:
                    scores_dict[key_str] = value_list
                else:
                    scores_dict[int(key_str)] = value_list

        #write saved scores
        player_index = -1
        for player in scores_dict:

            #write player ID
            player_index += 1
            textbox = manual_player_input_boxes[player_index]
            textbox.insert(tk.END, player)

            #write scores       
            for score in range(map_count):
                textbox = manual_score_input_boxes[player_index][score]
                textbox.insert(tk.END, scores_dict[player][score])
    else:
        add_player_manual_scores(m_root, manual_player_input_boxes, map_count, team_vs)

    ##make submit button active upon enter press

    # Bind the Enter key to the function when the Toplevel is in focus
    m_root.bind("<Return>", lambda event: on_closing_manual_scores(m_root, manual_player_input_boxes, manual_score_input_boxes, m_remember_var, team_vs))
    
    # Set focus on the Toplevel
    m_root.focus_set()

    # Optional: Unbind when the Toplevel window loses focus
    def on_focus_out(event):
        m_root.unbind("<Return>")

    def on_focus_in(event):
        m_root.bind("<Return>", lambda event: on_closing_manual_scores(m_root, manual_player_input_boxes, manual_score_input_boxes, m_remember_var, team_vs))

    # Bind focus out event to unbind the Enter key
    m_root.bind("<FocusOut>", on_focus_out)
    m_root.bind("<FocusIn>", on_focus_in)
    
    ##

    #start the GUI event loop, and wait until window is closed
    m_root.wait_window()

#acronym solver
def on_closing_acronym_solver(a_root: ctk.CTkToplevel, acronym_inputboxes: list, dublicated_acronyms: list, team_vs: bool):
    global player_data
    global acronym_warning_text
    global seeding
    outer_root.focus_set()

    if team_vs:
        #wipe old acronyms
        for team in dublicated_acronyms:
            seeding[team, 0] = ''

        for team in range(len(dublicated_acronyms)):
            new_acronym = acronym_inputboxes[team].get().upper()

            #check if new acronym is taken
            for acronym in list(seeding[:, 0]):
                if str(acronym)==new_acronym:
                    acronym_warning_text.grid_forget()
                    acronym_warning_text = ctk.CTkLabel(a_root, text=f'{new_acronym} is already taken')
                    acronym_warning_text.grid(row=number_of_rows(a_root), padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')
                    return

            #save new acronym
            seeding[dublicated_acronyms[team], 0] = new_acronym

    else:
        #wipe old acronyms
        for player in dublicated_acronyms:
            player_data[player]['acronym'] = ''

        #set player data acronyms to new edited acronym
        for player in range(len(dublicated_acronyms)):
            new_acronym = acronym_inputboxes[player].get().upper()

            #check if new acronym is taken
            for other_player in player_data:
                if player_data[other_player]['acronym']==new_acronym:
                    acronym_warning_text.grid_forget()
                    acronym_warning_text = ctk.CTkLabel(a_root, text=f'{new_acronym} is already taken')
                    acronym_warning_text.grid(row=number_of_rows(a_root), padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')
                    return

            player_data[dublicated_acronyms[player]]['acronym'] = new_acronym

    a_root.destroy()

def acronym_solver(dublicated_acronyms: list, team_vs: bool):
    global player_data
    acronym_inputboxes = []

    #create the main application window
    a_root = ctk.CTkToplevel(outer_root)
    a_root.title("Dublicated Acronyms")

    #create title
    if team_vs:
        title = ctk.CTkLabel(a_root, text="The following teams have been assigned identical acronyms. Please write custom acronyms")
    else:
        title = ctk.CTkLabel(a_root, text="The following players have been assigned identical acronyms. Please write custom acronyms")
    title.grid(column=0, columnspan=2, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    #write all players with dublicated acronyms, and make an entry to edit acronym
    current_row = 1
    for team in dublicated_acronyms:
        acronym_inputbox = ctk.CTkEntry(a_root, width=70, validate='key', validatecommand=(outer_root.register(non_digit_chararcter_limit_creator(5)), '%P'))

        if team_vs:
            team_label = ctk.CTkLabel(a_root, text=seeding[team, 1]) #write teamname
            team_label.grid(row=current_row, padx=GUI_xspacing, pady=GUI_yspacing)

            acronym_inputbox.insert(tk.END, seeding[team, 0]) #write old acronym
        else:
            player_label = ctk.CTkLabel(a_root, text=player_data[team]['username']) #write player name
            player_label.grid(row=current_row, padx=GUI_xspacing, pady=GUI_yspacing)

            acronym_inputbox.insert(tk.END, player_data[team]['acronym']) #write old acronym

        acronym_inputbox.grid(row=current_row, column=1, padx=GUI_xspacing, pady=GUI_yspacing)
        acronym_inputboxes.append(acronym_inputbox)
        current_row += 1

    #set delete protocol
    a_root.protocol("WM_DELETE_WINDOW", lambda: on_closing_acronym_solver(a_root, acronym_inputboxes, dublicated_acronyms, team_vs))
    
    #make submit button (just a close window button)
    close_acronym_solver_button = ctk.CTkButton(a_root, text="Submit", command=lambda: on_closing_acronym_solver(a_root, acronym_inputboxes, dublicated_acronyms, team_vs))
    close_acronym_solver_button.grid(row=number_of_rows(a_root), padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

    ##make submit button active upon enter press

    # Bind the Enter key to the function when the Toplevel is in focus
    a_root.bind("<Return>", lambda event: on_closing_acronym_solver(a_root, acronym_inputboxes, dublicated_acronyms, team_vs))
    
    # Set focus on the Toplevel
    a_root.focus_set()

    # Optional: Unbind when the Toplevel window loses focus
    def on_focus_out(event):
        a_root.unbind("<Return>")

    def on_focus_in(event):
        a_root.bind("<Return>", lambda event: on_closing_acronym_solver(a_root, acronym_inputboxes, dublicated_acronyms, team_vs))

    # Bind focus out event to unbind the Enter key
    a_root.bind("<FocusOut>", on_focus_out)
    a_root.bind("<FocusIn>", on_focus_in)
    
    ##

    #start the GUI event loop, and wait until window is closed
    a_root.wait_window()

#other functions
def terminate_script():
    global script_terminating
    script_terminating = True
    terminate_button.configure(state="disabled")

def disable_widgets(window):
    # Disable all widgets
    for widget in window.winfo_children():
        if isinstance(widget, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkCheckBox)):
            widget.configure(state="disabled")

        #if widget is a frame, disable all widget within the frame
        elif isinstance(widget, ctk.CTkFrame) and widget.winfo_name()!='!ctkframe6': #ignore frame6 (feedback buttons)
            disable_widgets(widget)

    # Enable terminate button
    terminate_button.configure(state="normal")

def enable_widgets(window):
    # Disable all widgets
    for widget in window.winfo_children():
        if isinstance(widget, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkTextbox, ctk.CTkCheckBox)):
            widget.configure(state="normal")

        #if widget is a frame, enable all widget within the frame
        elif isinstance(widget, ctk.CTkFrame):
            enable_widgets(widget)

    # Enable terminate button
    terminate_button.configure(state="disabled")
    terminal_text_widget.configure(state="disabled")

def number_of_rows(window) -> int:
    #loop through all widgets in the given window, get widget with the highest index, add one to get number of rows
    output = 0
    for widget in window.grid_slaves():
        if int(widget.grid_info()["row"])>output:
            output = int(widget.grid_info()["row"])
    return output+1

def row_of(widget) -> int:
    return int(widget.grid_info()["row"])

def move_widgets(move_root, row: int, distance: int):
    #loop through all widgets in the given window, move the widgets that are below the given row
    for widget in move_root.grid_slaves():
        widget_row = int(widget.grid_info()["row"])
        if widget_row > row:
            widget.grid(row=widget_row-distance)

def make_splitpiece():
    ctk.CTkLabel(root, text='', width=475, height=1, fg_color='grey90', corner_radius=10, font=('font3', 5)).pack(pady=GUI_yspacing)

def add_lobby():
    #create textbox
    new_textbox = ctk.CTkEntry(lobby_input_box_frame, width=100, validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(9)), '%P'))

    #place textbox
    new_textbox.grid(row=floor(len(lobby_input_boxes)/4), column=len(lobby_input_boxes)%4, padx=GUI_xspacing, pady=GUI_yspacing)
    lobby_input_boxes.append(new_textbox)

def toggle_match_for_3rd_place():

    #place 3rd place checkbox upon event of clicking single elimination checkbox
    if single_elimination_var.get():
        move_widgets(settings_frame, row_of(single_elimination_checkbox), -1)
        match_for_3rd_place_checkbox.grid(row=row_of(single_elimination_checkbox)+1, padx=(20,0), pady=GUI_yspacing, sticky='w')
    
    #if the event was "unchecking" the checkbox, then remove 3rd place checkbox and set it to false
    else:
        match_for_3rd_place_var.set(False)
        move_widgets(settings_frame, row_of(single_elimination_checkbox)+1, 1)
        match_for_3rd_place_checkbox.grid_forget()

def toggle_team_vs():

    #place teams input box upon event of clicking teamVS checkbox
    if team_vs_var.get():
        team_vs_input_box.grid(row=number_of_rows(settings_frame), sticky='w')

    #if the event was "unchecking" the checkbox, then remove the textbox
    else:
        team_vs_input_box.grid_remove()

def toggle_redemption():

    #place teams input box upon event of clicking teamVS checkbox
    if redemption_var.get():
        move_widgets(settings_frame, row_of(redemption_checkbox), -1)
        redemption_inputbox.grid(row=row_of(redemption_checkbox)+1, padx=(20,0), pady=GUI_yspacing, sticky='w')

    #if the event was "unchecking" the checkbox, then remove the textbox
    else:
        redemption_inputbox.delete(0, "end")
        move_widgets(settings_frame, row_of(redemption_checkbox)+1, 1)
        redemption_inputbox.grid_remove()

def GUI_terminal_print(string: str):
    #after is apparently some safe method i should use
    root.after(0, terminal_text_widget.configure(state=tk.NORMAL))
    root.after(0, terminal_text_widget.insert(tk.END, string+'\n'))
    root.after(0, terminal_text_widget.configure(state=tk.DISABLED))
    root.after(0, terminal_text_widget.see(tk.END))
    root.after(0, terminal_text_widget.update())

def update_terminal_text(current: int, total: int):
    #delete last line if not first update statement and write new line, else just write new line
    terminal_text = f'\n({current}/{total})'
    if current!=1:
        #save and delete terminal text
        text = terminal_text_widget.get("1.0", "end-1c")
        lines = text.split('\n')
        old_terminal_text = '\n'.join(lines[:-1])
        terminal_text_widget.configure(state=tk.NORMAL)
        terminal_text_widget.delete('1.0', tk.END)

        #rewrite terminal with new last line
        terminal_text_widget.insert(tk.END, old_terminal_text)
        terminal_text_widget.insert(tk.END, terminal_text)
        terminal_text_widget.configure(state=tk.DISABLED)
        terminal_text_widget.see(tk.END)
        terminal_text_widget.update()
    else:
        terminal_text_widget.configure(state=tk.NORMAL)
        terminal_text_widget.insert(tk.END, terminal_text)
        terminal_text_widget.configure(state=tk.DISABLED)
        terminal_text_widget.see(tk.END)
        terminal_text_widget.update()

def delete_newline_character():
    current_text = terminal_text_widget.get("1.0", "end-1c")
    new_text = current_text[:-1]
    terminal_text_widget.configure(state=tk.NORMAL)
    terminal_text_widget.delete("1.0", tk.END)
    terminal_text_widget.insert("1.0", new_text)
    terminal_text_widget.configure(state=tk.DISABLED)

def delete_lastline():
    current_text = terminal_text_widget.get("1.0", "end-1c")
    last_index = current_text.rfind('\n')
    new_text = current_text[:last_index]
    terminal_text_widget.configure(state=tk.NORMAL)
    terminal_text_widget.delete("1.0", tk.END)
    terminal_text_widget.insert("1.0", new_text)
    terminal_text_widget.configure(state=tk.DISABLED)

def select_all(event):
    #what ctrl+a does
    if isinstance(event.widget, tk.Text):
        event.widget.tag_add('sel', "1.0", tk.END)

def entry_chararcter_limit_creator(limit: int):
    
    #return a function that can be registered to return a boolean value to determine if the event is valid
    def character_limit_validator(new_text: str):
        return len(new_text)<=limit and new_text.isdigit() or new_text==''
    
    return character_limit_validator

def non_digit_chararcter_limit_creator(limit: int):
    
    #return a function that can be registered to return a boolean value to determine if the event is valid
    def character_limit_validator(new_text: str):
        return len(new_text)<=limit
    
    return character_limit_validator

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None

        # Bind events to the widget
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return

        # Create a Toplevel widget for the tooltip
        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.geometry(f"+{self.widget.winfo_rootx() + 20}+{self.widget.winfo_rooty() + 20}")

        # Add a CTkLabel to display the tooltip text with modern style
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, justify="left", fg_color="gray75", corner_radius=8, 
                             text_color="black", padx=10, pady=5)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

###script execution

#requesting data:
def request_scores(api: Ossapi, mp: int) -> dict:
    output = {}
    players = []
    lobby = api.match(mp)

    # make a list of the players
    for event in lobby.events:
        if event.game != None and event.game.end_time != None:
            for player in event.game.scores:
                players.append(player.user_id)
            break 

    for player in players: #loop through each user, and append the score from each map that was set with this user ID
        player_scores = []
        for event in lobby.events:
            if event.game != None and event.game.end_time != None:
                for score in event.game.scores:
                    if score.user_id==player:
                        player_scores.append(score.score)
                        break
        output[player] = player_scores
    return output

def get_mod_count(api: Ossapi, mp: int, included_mods: list) -> dict:
    output = {}

    for mod in included_mods: #make every mod in output equal 0
        output[mod] = 0

    for event in api.match(mp).events: #loop through events
        if event.game != None and event.game.end_time != None: # events that are maps playd
            if event.game.mods == ['NF']: #add one for all the maps that are nomod
                output['nm'] += 1
            else:
                for mod in included_mods: #add number of all other mods
                    if len(mod)==2:
                        if event.game.mods == ['NF', mod.upper()]:
                            output[mod] += 1
                            break #continue to next map
                    else:
                        mod_split = [mod[i:i+2].upper() for i in range(0, len(mod), 2)]
                        if event.game.mods == ['NF'] + mod_split:
                            output[mod] += 1
                            break #continue to next map
    return output

def get_map_list(api: Ossapi, mp: int) -> list:
    output = []

    for event in api.match(mp).events:
        if event.game != None and event.game.end_time != None:
            output.append(event.game.beatmap_id)
    return output

def get_included_mods(api: Ossapi, mp: int) -> list:
    output = []
    for event in api.match(mp).events:
        if event.game != None and event.game.end_time != None:
            if len(event.game.mods)==1:
                if 'nm' not in output:
                    output.append('nm')
                '''elif event.game.mods[-1].lower() not in output:
                output.append(event.game.mods[-1].lower())'''
            else:
                mod = ''.join(event.game.mods[1:]).lower()
                if mod not in output:
                    output.append(mod)
    return output

def request_playerdata(player) -> dict:
    name = player.username
    output = {
        'username': name,
        'acronym': name[:3].upper(),
        'nationality': player.country_code,
        'rank': player.rank_history.data[-1],
        'cover': player.cover_url
    }
    return output

def request_scores_teams(api: Ossapi, mp: int, teams: dict) -> dict:
    output = {}

    #count every time a map is play'd, to determine how many scores a team should have at any given point
    count = 0

    current_match = api.match(mp, after=0)
    while True:
        for event in current_match.events: #loop through all events
            if event.game != None and event.game.end_time != None: #ignore events where a map is not play'd
                count += 1
                for score in event.game.scores: #loop through all scores in a specific map
                    for team, players in teams.items(): #find the team containing the player who set this specific score
                        if score.user_id in players:
                            if team in output: #add team to output if not yet added
                                if len(output[team])<count: #create new score if this is the first score set by this team
                                    output[team].append(score.score)
                                else: #else add score to existing score
                                    output[team][-1] += score.score
                            else:
                                output[team] = [score.score]
                            break #stop looping through teams list
        
        #if lobby contains more than 100 event, the first event will be left out. So we run the sequence again as long as there are more than 100 events left
        if len(current_match.events)==100:
            current_match = api.match(mp, after=current_match.events[-1].id-10) #set current match to only include events after the last event of last 'current_match', with a buffer of minus 19
        else:
            break
    return output

def request_playerdata_teams(api: Ossapi, player_id: int)-> dict:
    player = api.user(player_id)
    name = player.username
    return {'username': name,
            'acronym': name[:3].upper(),
            'nationality': player.country_code,
            'rank': player.rank_history.data[-1],
            'cover': player.cover_url}

#functions:
def convert_scores_to_np(scores: dict) -> np.ndarray:
    output = np.array([], dtype=int) #define blank values to be used later
    temp_arr = np.array([], dtype=int)

    for player in scores: #set player id at first index in the array
        output = np.concatenate((output, np.array([player])))

    output = output.reshape(-1,1) #convert 1D array to 2D array with one column

    for round in range(len(next(iter(scores.values())))): #set 2nd column as nm1, 3rd column as nm2 and so on..
        for player in scores: #make a 1D array of all scores in a specific round
            temp_arr = np.concatenate((temp_arr, np.array([scores[player][round]])))
        output = np.hstack((output, temp_arr.reshape(-1,1))) #convert temp to 2D array and add it ontu the back of arr
        temp_arr = np.array([], dtype=int) #reset temp for next loop
    return output

def get_seeding(scores: np.ndarray, seeding_method: str, mappool_size: int) -> np.ndarray:
    global seeding
    if seeding_method!="Total Score":
        map_seeds = np.zeros(scores.shape, dtype=int)[:, 1:]
        number_of_players = scores.shape[0]
        number_of_rounds = scores.shape[1]-1
        for round in range(number_of_rounds):
            numbers = scores[:,round+1].astype(int)
            seeds = number_of_players-np.argsort(numbers).argsort()
            map_seeds[:,round] = seeds
    else:
        map_seeds = scores[:, 1:]
    if seeding_method=="Zipf's Law":
        row_sums = np.sum(100/map_seeds+mappool_size*1.4, axis=1)
        sorted_indices = np.argsort(row_sums)[::-1]
    else:
        sorted_indices = np.argsort(map_seeds.sum(1))
    final_seed = np.empty_like(sorted_indices)
    if seeding_method!="Total Score":
        final_seed[sorted_indices] = np.arange(1, len(sorted_indices)+1)
    else:
        final_seed[sorted_indices] = np.arange(len(sorted_indices), 0, -1)
    seeding = np.column_stack([scores[:,0], map_seeds, final_seed])

def get_map_seeds(seeding: np.ndarray, player: int, mod_count: dict, maps: list, mod: int, scores_np: np.ndarray, included_mods: list, team_vs) -> dict:
    output = {}

    #looking at a slice from first index to last index. Move the slice for each iteration as mod progresses
    first_index = 1
    for m in range(mod):
        first_index += mod_count[included_mods[m]]

    last_index = 1+mod_count[included_mods[mod]]
    for m in range(mod):
        last_index += mod_count[included_mods[m]]
    
    if team_vs:
        first_index += 1 #seeding has format shifted by one in teams tournaments
        last_index += 1

    #define output elements
    map_seeds =[]
    output['Beatmaps'] = map_seeds #will be appended during the loop below
    output['Mod'] = included_mods[mod].upper() #find current mod
    output['Seed'] = int(np.argsort(seeding[:,first_index:last_index].astype(int).sum(1)).argsort()[player])+1 #sort seedings using same method as in get_seeding()

    #loop through each map in the current mod, and append results of that map
    if team_vs: #team seeding has different format
        for map in range(len(seeding[(player)]))[first_index:last_index]:
            beatmap = {'Id': int(maps[map-2]), 
                    'Score': int(float(scores_np[(player, map-1)])), 
                    'Seed': int(seeding[(player, map)])}
            map_seeds.append(beatmap.copy())
    else:
        for map in range(len(seeding[(player)]))[first_index:last_index]:
            beatmap = {'Id': int(maps[map-1]), 
                    'Score': int(float(scores_np[(player, map)])), 
                    'Seed': int(seeding[(player, map)])}
            map_seeds.append(beatmap.copy())
    return output

def seeding_matchups(lobby_matchups: list) -> dict:
    output = {}
    count = 0
    for seed in lobby_matchups:
        count += 1
        output[str(count)] = seed
    return output

def recursion(n: int) -> int:
    if n==1:
        return 1
    else:
        return int(2**n+recursion(n-1))

def recursion_with_grands(n: int) -> int:
    if n==2:
        return 7
    else:
        return int(2**n+recursion_with_grands(n-1))

def number_of_rounds(players: int) -> int:
        
    log_base2 = log(players) / log(2)
    lower_bound = floor(log_base2)
    upper_bound = ceil(log_base2)
    
    midpoint = (2**lower_bound+2**upper_bound)/2
    
    if players > midpoint:
        return upper_bound
    else:
        return lower_bound

def write_data(teams: list, scores_np: np.ndarray) -> None:

    #create a txt file of player IDs sorted by seed
    with open('Extra data/player IDs.txt', 'w') as  file:
        for player in teams:
            file.write(str(player['Players'][0]['id'])+'\n')
    
    #create file for player names sorted by seed
    with open('Extra data/players.txt', 'w') as  file:
        for player in teams:
            file.write(str(player['FullName'])+'\n')
    
    # Get the indices to rearange seeding with highest seed at the top
    sorted_indices = np.argsort(seeding[:, -1])

    #create file of seeds
    with open('Extra data/seeding.txt', 'w') as file:
        i = 0
        for row in seeding[sorted_indices][:, 1:]:
            # Convert each row to a tab-separated string
            row_str = teams[i]['FullName']+'\t'+'\t'.join(map(str, row))
            # Write the row string to the file, followed by a newline
            file.write(row_str + '\n')
            i += 1
    
    #create file of scores
    with open('Extra data/scores.txt', 'w') as file:
        i = 0
        for row in scores_np[sorted_indices][:, 1:]:
            # Convert each row to a tab-separated string
            row_str = teams[i]['FullName']+'\t'+'\t'.join(map(str, row))
            # Write the row string to the file, followed by a newline
            file.write(row_str + '\n')
            i += 1


#matches:
def get_matches(seeding: np.ndarray, first_round: str, number_of_qualifying_players: int, leftover_players: int, double_elimination: bool, team_vs: bool) -> list:
    #define variables
    global player_data
    output = []

    #make a dictionary with seeds as keys and the corrosponding player IDs/team name as values
    seed_is_player = {}
    if team_vs:
        for team in seeding:
            seed_is_player[int(team[-1])] = str(team[1])
    else:
        for player in seeding:
            seed_is_player[int(player[-1])] = int(player[0])
    
    #'matchups_list' describes what seed will be assigned to each lobby. ex: lobby one has seed one, lobby two has seed 64, lobby three has seed 32, lobby four has seed 33..
    matchups_dict = {'Semi Finals': [1,2],
                        'Quarter Finals': [1,4,2,3],
                        'Round of 16': [1,8,4,5,2,7,3,6],
                        'Round of 32': [1,16,8,9,4,13,5,12,2,15,7,10,3,14,6,11],
                        'Round of 64': [1,32,16,17,8,25,9,24,4,29,13,20,5,28,12,21,2,31,15,18,7,26,10,23,3,30,14,19,6,27,11,22],
                        'Round of 128': [1,64,32,33,16,49,17,48,8,57,25,40,9,56,24,41,4,61,29,36,13,52,20,45,5,60,28,37,12,53,21,44,2,63,31,34,15,50,18,47,7,58,26,39,10,55,23,42,3,62,30,35,14,51,19,46,6,59,27,38,11,54,22,43]}
    
    matchups_list = matchups_dict[first_round]

    #define variables
    participants = len(matchups_list)*2
    rounds = int(log(len(matchups_list))/log(2))+1
    matchups = seeding_matchups(matchups_list)

    #losers coordinates will count count for each winners lobby made
    losers_y_start_cord = 40

    #make first round lobbies at X=0 and Y progressively increases. Lobby ID will increase by one for each lobby created
    for i in range(1, int(participants/2+1)):
        losers_y_start_cord += 120
        output.append(
        {
            "ID": i,
            "Team1Acronym": "",
            "Team1Score": None,
            "Team2Acronym": "",
            "Team2Score": None,
            "Completed": False,
            "Losers": False,
            "PicksBans": [],
            "Current": False,
            "Date": "2023-12-20T17:14:41.0615771+01:00",
            "ConditionalMatches": [],
            "Position": {
                "Y": 120*(i-1)
            },
            "Acronyms": [
                "",
                ""
            ]
            })

    #add the players to the first round lobbies
    if team_vs:
        for lobby in range(int(participants/2)):
            team1 = seed_is_player[matchups[str(lobby+1)]]
            team2 = seed_is_player[1+participants-matchups[str(lobby+1)]]

            team1_index = np.where(seeding[:, 1] == team1)[0]
            team2_index = np.where(seeding[:, 1] == team2)[0]

            output[lobby]['Team1Acronym'] = seeding[team1_index[0], 0]
            output[lobby]['Team2Acronym'] = seeding[team2_index[0], 0]

    else:
        for lobby in range(int(participants/2)):
            output[lobby]['Team1Acronym'] = player_data[seed_is_player[matchups[str(lobby+1)]]]['acronym']
            output[lobby]['Team2Acronym'] = player_data[seed_is_player[1+participants-matchups[str(lobby+1)]]]['acronym']    

    #make variable that will be increase by one every time a new lobby is created
    current_lobby = int(participants/2)

    #first lobby of each round has a Y-coordinate that varies with a difference
    dif = 60
    n = 60

    #create the winners bracket
    for round in range(rounds)[1:]:
        for i in range(1, int(participants/2**(round+1)+1)):
            current_lobby += 1
            output.append({
                "ID": current_lobby,
                "Team1Acronym": "",
                "Team1Score": None,
                "Team2Acronym": "",
                "Team2Score": None,
                "Completed": False,
                "Losers": False,
                "PicksBans": [],
                "Current": False,
                "Date": "2023-12-20T17:14:41.0615771+01:00",
                "ConditionalMatches": [],
                "Position": {
                    "X": 180*round,
                    "Y": n+2**round*120*(i-1)
                },
                "Acronyms": [
                    "",
                    ""
                ]
                })
        dif *= 2
        n += dif
    
    num_of_winner_lobbies = len(output)

    if double_elimination:
        n -= dif

        #create losers bracket up until finals
        for round in range(1, 1+rounds-2):
            for i in range(1, 1+int(participants/2**(round+1))):
                current_lobby += 1
                output.append({
                    "ID": current_lobby,
                    "Team1Acronym": "",
                    "Team1Score": None,
                    "Team2Acronym": "",
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": True,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "X": 180+360*(round-1),
                        "Y": losers_y_start_cord+2**(round-1)*(i-1)*100
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
            for i in range(1, 1+int(participants/2**(round+1))):
                current_lobby += 1
                output.append({
                    "ID": current_lobby,
                    "Team1Acronym": "",
                    "Team1Score": None,
                    "Team2Acronym": "",
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": True,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "X": 360+360*(round-1),
                        "Y": losers_y_start_cord+2**(round-1)*(i-1)*100-40
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
                
        #create losers Finals
        current_lobby += 1
        output.append({
                    "ID": current_lobby,
                    "Team1Acronym": "",
                    "Team1Score": None,
                    "Team2Acronym": "",
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": True,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "X": 360*(rounds-1)-180,
                        "Y": losers_y_start_cord
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
        
        #create losers Grand Finals
        current_lobby += 1
        output.append({
                    "ID": current_lobby,
                    "Team1Acronym": "",
                    "Team1Score": None,
                    "Team2Acronym": "",
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": True,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "X": 360*(rounds-1),
                        "Y": n+int((losers_y_start_cord-n)/3*2)
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
        
        #create Grand Finals
        current_lobby += 1
        output.append({
                    "ID": current_lobby,
                    "Team1Acronym": "",
                    "Team1Score": None,
                    "Team2Acronym": "",
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": False,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "X": 360*(rounds-1)+180,
                        "Y": n+80
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
        
        #create bracket reset
        current_lobby += 1
        output.append({
                    "ID": current_lobby,
                    "Team1Acronym": "",
                    "Team1Score": None,
                    "Team2Acronym": "",
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": False,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "X": 360*rounds,
                        "Y": n+100
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
    
    if leftover_players:

        #get list of indexes for matchups sorted with lowest seed first
        indexed_list = list(enumerate(matchups_list))
        sorted_indexed_list = sorted(indexed_list, key=lambda x: x[1])
        matchup_indexes = [index for index, value in sorted_indexed_list]

        #start by solving the case where leftover players is less than half required for a full round. ex ro16-24 or ro32-48
        if leftover_players<=number_of_qualifying_players/3:

            #shift all lobbies one space to the side to make room for leftover players
            for lobby in output:
                if "X" in lobby["Position"]:
                    lobby["Position"]["X"] += 180
                else:
                    lobby["Position"]["X"] = 180

            #create lobbies
            for player in range(leftover_players):
                current_lobby += 1
                next_lobby = output[matchup_indexes[player]]

                #get acronym of additional team
                if team_vs:
                    team2 = seed_is_player[participants+player]
                    team2_index = np.where(seeding[:, 1] == team2)[0]
                    team2_acronym = seeding[team2_index[0], 0]
                else:
                    team2_acronym = player_data[seed_is_player[participants+player+1]]['acronym']

                #create winner lobbies
                output.append({
                    "ID": current_lobby,
                    "Team1Acronym": next_lobby["Team2Acronym"],
                    "Team1Score": None,
                    "Team2Acronym": team2_acronym,
                    "Team2Score": None,
                    "Completed": False,
                    "Losers": False,
                    "PicksBans": [],
                    "Current": False,
                    "Date": "2023-12-20T17:14:41.0615771+01:00",
                    "ConditionalMatches": [],
                    "Position": {
                        "Y": next_lobby["Position"]["Y"]+40
                    },
                    "Acronyms": [
                        "",
                        ""
                    ]
                    })
                
                #unassign player from next lobby
                next_lobby["Team2Acronym"] = ""
            if double_elimination:
                if leftover_players<=number_of_qualifying_players/5: #the loser lobbies are divided into two halves as well. ex ro17-20 or ro33-40
                    for player in range(leftover_players):
                        current_lobby += 1
                        next_lobby = output[int(matchup_indexes[player]/2)+num_of_winner_lobbies]

                        #create loser lobbies
                        output.append({
                            "ID": current_lobby,
                            "Team1Acronym": "",
                            "Team1Score": None,
                            "Team2Acronym": "",
                            "Team2Score": None,
                            "Completed": False,
                            "Losers": True,
                            "PicksBans": [],
                            "Current": False,
                            "Date": "2023-12-20T17:14:41.0615771+01:00",
                            "ConditionalMatches": [],
                            "Position": {
                                "X": 180,
                                "Y": next_lobby["Position"]["Y"]+40
                            },
                            "Acronyms": [
                                "",
                                ""
                            ]
                            })
                else: #ro21-24 or ro41-48

                    #widen lobbies
                    iterator = 0
                    trigger = -1
                    x_position = 0
                    y_space = 120
                    for lobby in output:
                        if lobby["Losers"]:

                            if x_position!=lobby["Position"]["X"]: #when next column begins
                                iterator = 0 #going back to the top

                                #for every second column the y_space needed doubles
                                trigger += 1
                                if trigger == 2:
                                    y_space *= 2
                                    trigger = 0
                            x_position = lobby["Position"]["X"]

                            #move lobby
                            lobby["Position"]["Y"] += y_space*iterator+60
                            iterator += 1
                    
                    #create lobbies
                    reference = output[number_of_qualifying_players-leftover_players-1]["Position"]["Y"]-40
                    for player in range(leftover_players):
                        current_lobby += 1
                        output.append({
                            "ID": current_lobby,
                            "Team1Acronym": "",
                            "Team1Score": None,
                            "Team2Acronym": "",
                            "Team2Score": None,
                            "Completed": False,
                            "Losers": True,
                            "PicksBans": [],
                            "Current": False,
                            "Date": "2023-12-20T17:14:41.0615771+01:00",
                            "ConditionalMatches": [],
                            "Position": {
                                "X": 180,
                                "Y": reference+110*matchup_indexes[player]
                            },
                            "Acronyms": [
                                "",
                                ""
                            ]
                            })
        
        else: #solving ro25-31/ro48-63

            #delete the excess lobbies and move the higher seed to next lobby
            lobbies_to_delete = []
            loser_index_start = (number_of_qualifying_players-leftover_players)*2
            for index in matchup_indexes[::-1][leftover_players:]:
                output[number_of_qualifying_players-leftover_players+index//2]["Team1Acronym"] = output[index]["Team1Acronym"]
                lobbies_to_delete.append(output[index])
                if double_elimination:
                    lobbies_to_delete.append(output[index//2+loser_index_start])
            for lobby in lobbies_to_delete:
                output.remove(lobby)

    else:
        matchup_indexes = None #this value will not be used

    return (output, matchup_indexes)

def offset_seeding(seeding: np.ndarray, number_of_qualifying_players: int) -> np.ndarray:

    #offset the seeding so first unqualified player becomes seed one
    final_seed = seeding[:, -1].astype(int)
    final_seed -= number_of_qualifying_players
    return np.column_stack([seeding[:, :-1], final_seed])

def merge_redemption_bracket(main_bracket: list, redemption_bracket: list, redemption_lobby_id_start: int):

    #get size of main bracket
    redemption_y_start = 0
    for lobby in main_bracket:
        lobby_y = lobby["Position"]["Y"]
        if lobby_y>redemption_y_start:
            redemption_y_start = lobby_y
    
    #make some space between the two brackets
    redemption_y_start += 360

    #move redemption bracket in position
    for lobby in redemption_bracket:
        lobby["ID"] += redemption_lobby_id_start #make new IDs for redemption lobbies

        if "Y" in lobby["Position"]:
            lobby["Position"]["Y"] += redemption_y_start
        else:
            lobby["Position"]["Y"] = redemption_y_start
    
    main_bracket.extend(redemption_bracket)
    return main_bracket

#rounds:
def get_rounds(rounds_list: list, number_of_qualifying_players: int, leftover_players: int, num_of_matches: int, double_elimination: bool) -> list:
    #define variables
    output = []
    rounds = len(rounds_list)

    participants_dict = {'Semi Finals': 4,
                         'Quarter Finals': 8,
                         'Round of 16': 16,
                         'Round of 32': 32,
                         'Round of 64': 64,
                         'Round of 128': 128,
                         'Redemption - Semi Finals': 4,
                         'Redemption - Quarter Finals': 8,
                         'Redemption - Round of 16': 16,
                         'Redemption - Round of 32': 32,
                         'Redemption - Round of 64': 64,
                         'Redemption - Round of 128': 128}

    participants = participants_dict[rounds_list[-1]]

    #create rounds
    for round in rounds_list:
        output.append({
        "Name": round,
        "Description": "",
        "BestOf": 9,
        "Beatmaps": [],
        "StartDate": "2023-10-27T22:39:28+00:00",
        "Matches": []
        })

    #assign winners bracket lobbies to their respective rounds
    count = 0
    for round in range(rounds):
        lobby_number = count
        for lobby_id in range(1, int(participants/2**(round+1))+1):
            count += 1
            output[-1-round]['Matches'].append(lobby_id + lobby_number)

    if double_elimination:
        #assign first round losers bracket lobbies to their respective rounds
        for lobby_id in range(int(participants/4)):
            output[-2]['Matches'].append(lobby_id+participants)

        #assign the other lobbies
        current = participants+int(participants/4)
        for round in range(rounds-2):
            for lobby_id in range(int(2**(rounds-2)/2**round+2**(rounds-2)/2**round/2)):
                output[-3-round]['Matches'].append(current)
                current += 1
        
        #create 'Grand Finals' round
        output.insert(0, {
        "Name": 'Grand Finals',
        "Description": "",
        "BestOf": 9,
        "Beatmaps": [],
        "StartDate": "2023-10-27T22:39:28+00:00",
        "Matches": []
        })

        #assign Grand Finals lobbies to the round
        for lobby_id in range(3):
            output[0]['Matches'].append(current+lobby_id)
        
        #assign leftover lobbies
        if leftover_players<=number_of_qualifying_players/3:
            for lobby in range(num_of_matches-leftover_players*2+1, num_of_matches-leftover_players+1):
                output[-1]["Matches"].append(lobby)
            for lobby in range(num_of_matches-leftover_players+1, num_of_matches+1):
                output[-2]["Matches"].append(lobby)
    else: #half ammount of leftover lobbies if single elimination
        if leftover_players<=number_of_qualifying_players/3:
            for lobby in range(num_of_matches-leftover_players+1, num_of_matches+1):
                output[-1]["Matches"].append(lobby)
    
    return output

def merge_redemption_rounds(main_rounds: list, rounds_list: list, redemption_players: int, leftover_players, num_of_matches: int, main_bracket_size: int, double_elimination: bool):
    redemption_rounds = get_rounds(['Redemption - '+round for round in rounds_list], redemption_players, leftover_players, num_of_matches, double_elimination)
    redemption_rounds[0]["Name"] = 'Redemption - Grand Finals'

    #add 'main_bracket_size' to every match
    for round in redemption_rounds:
        round["Matches"] = [round + main_bracket_size for round in round["Matches"]]
    
    main_rounds.extend(redemption_rounds)

    return main_rounds


#teams:
def get_teams_1v1(scores: np.ndarray, number_of_players: int, maps: list, mod_count: dict, included_mods: list) -> list:
    #define variables
    global player_data
    global seeding
    output = []

    #append all teams
    for player in range(number_of_players):
        #define variables
        final_seed = seeding[(player)][-1]
        mod_seeds = []
        for mod in range(len(included_mods)):
            mod_seeds.append(get_map_seeds(seeding, player, mod_count, maps, mod, scores, included_mods, False))
        
        #write team
        current = player_data[int(seeding[(player)][0])]
        output.append(
        {
        "FullName": current['username'],
        "FlagName": current['nationality'],
        "Acronym": current['acronym'],
        "SeedingResults": mod_seeds,
        "Seed": str(final_seed),
        "LastYearPlacing": 0,
        "AverageRank": current['rank'],
        "Players": [
            {
            "id": int(seeding[(player)][0]),
            "Username": current['username'],
            "country_code": current['nationality'],
            "Rank": current['rank'],
            "CoverUrl": current['cover']
            }
        ]
        }
        )
    #return the teams sorted with highest seed first
    return sorted(output, key=lambda x: int(x['Seed']))

def get_teams(scores: np.ndarray, number_of_teams: int, maps: list, mod_count: dict, included_mods: list, teams: dict) -> list:
    #define variables
    global player_data
    global seeding
    output = []

    #append all teams
    for team in range(number_of_teams):
        #define variables
        final_seed = seeding[(team)][-1]
        mod_seeds = []
        for mod in range(len(included_mods)):
            mod_seeds.append(get_map_seeds(seeding, team, mod_count, maps, mod, scores, included_mods, True))
        name = seeding[team, 1]
        player_ranks = []
        for player in teams[name]:
            player_ranks.append(player_data[player]['rank'])
        avg_rank = int(sum(player_ranks)/len(player_ranks))

        #write team
        output.append(
        {
        "FullName": name,
        "FlagName": player_data[teams[name][0]]['nationality'],
        "Acronym": seeding[team, 0],
        "SeedingResults": mod_seeds,
        "Seed": str(final_seed),
        "LastYearPlacing": 0,
        "AverageRank": avg_rank,
        "Players": []
        }
        )

        #add players to teams
        for player in teams[name]:
            output[-1]['Players'].append(
            {
            "id": player,
            "Username": player_data[player]['username'],
            "country_code": player_data[player]['nationality'],
            "Rank": player_data[player]['rank'],
            "CoverUrl": player_data[player]['cover']
            }
        )
    #return the teams sorted with highest seed first
    return sorted(output, key=lambda x: int(x['Seed']))            

#progressions:
def get_progression(rounds: int, number_of_qualfying_players: int, number_of_initial_lobbies: int, matchup_indexes: list, leftover_players: int, double_elimination: bool) -> list:
    #define variables
    output = []
    firstround_lobbies = 2**(rounds-1)
    current = firstround_lobbies
    progression_states = {
    'up': 'up_split',
    'up_split': 'down_split',
    'down_split': 'down',
    'down': 'up'
    }

    #cycle starts one step later if there is a round of leftover players (for the case of the first half of the leftover round)
    if leftover_players and leftover_players<=number_of_qualfying_players/3:
        cycle = 'up'
    else:
        cycle = 'down'

    #create winners bracket progressions
    for round in range(rounds)[1:]:
        for lobby in range(1, int(firstround_lobbies/2**round)+1):
            current += 1
            output.append({
            "SourceID": len(output)+1,
            "TargetID": current
            })
            output.append({
            "SourceID": len(output)+1,
            "TargetID": current
            })

    if double_elimination:
        #create winners final progression to Grands
        current += 1
        output.append({
                "SourceID": len(output)+1,
                "TargetID": current+int(recursion(rounds-1))+1
                })

        #create progressions to first round of losers
        if cycle=='down':

            #create variable that decides what winners lobby is connected to what losers lobby
            source_to_losers = 1

            for lobby in range(1,1+int(2**(rounds-2))):
                output.append({
                        "SourceID": source_to_losers,
                        "TargetID": current,
                        "Losers": True
                        })
                output.append({
                        "SourceID": source_to_losers+1,
                        "TargetID": current,
                        "Losers": True
                        })
                source_to_losers += 2
                current += 1

            #change state for the next cycle
            cycle = progression_states[cycle]
        else: #if cycle is 'up'
            source_to_losers = (number_of_qualfying_players-leftover_players)//2
            for lobby in range(1,1+int(2**(rounds-2))):
                output.append({
                        "SourceID": source_to_losers,
                        "TargetID": current,
                        "Losers": True
                        })
                output.append({
                        "SourceID": source_to_losers-1,
                        "TargetID": current,
                        "Losers": True
                        })
                source_to_losers -= 2
                current += 1
            source_to_losers = (number_of_qualfying_players-leftover_players)//2+1

            #change state for the next cycle
            cycle = progression_states[cycle]

        #create progressions for the rest of losers
        for round in range(1,1+rounds-2):

            #create first part of each losers round where a loser from the winners bracket face a winner from the losers
            #the losers progressing from the winners bracket can progress in four different states: down, up, up_split and down_split, starting with up
            reference = current
            number_of_matches = int(2**(rounds-2)/2**(round-1))
            if cycle=='up':
                to_current_loser = reference+number_of_matches-1
            elif cycle=='up_split':
                to_current_loser = reference+int(number_of_matches/2)-1
            elif cycle=='down_split':
                to_current_loser = reference+int(number_of_matches/2)
            else: #if 'down'
                to_current_loser = reference
            
            #for each lobby the script checks the current state and assigns the progressiong according to the rules of the state
            for lobby in range(1,1+int(2**(rounds-2)/2**(round-1))):
                if cycle=='up':
                    output.append({
                            "SourceID": source_to_losers,
                            "TargetID": to_current_loser,
                            "Losers": True
                            })
                    to_current_loser -= 1
                elif cycle=='up_split':
                    output.append({
                            "SourceID": source_to_losers,
                            "TargetID": to_current_loser,
                            "Losers": True
                            })
                    to_current_loser -= 1
                    if to_current_loser<reference:
                        to_current_loser += number_of_matches
                elif cycle=='down_split':
                    output.append({
                            "SourceID": source_to_losers,
                            "TargetID": to_current_loser,
                            "Losers": True
                            })
                    to_current_loser += 1
                    if to_current_loser>=reference+number_of_matches:
                        to_current_loser -= number_of_matches
                else:
                    output.append({
                            "SourceID": source_to_losers,
                            "TargetID": to_current_loser,
                            "Losers": True
                            })
                    to_current_loser += 1

                #set progression of winner comming from losers bracket
                output.append({
                        "SourceID": int(current-2**(rounds-2)/2**(round-1)),
                        "TargetID": current,
                        }) 
                
                #move to next lobby
                source_to_losers += 1
                current += 1
            
            #change state for the next cycle
            cycle = progression_states[cycle]
                
            #create second part of each losers round where winners of the loser bracket face eachother
            for lobby in range(1,1+int(2**(rounds-3)/2**(round-1))):
                output.append({
                        "SourceID": int(current-2**(rounds-2)/2**(round-1))+lobby-1,
                        "TargetID": current,
                        })
                output.append({
                        "SourceID": int(current-2**(rounds-2)/2**(round-1))+1+lobby-1,
                        "TargetID": current,
                        })  
                current += 1

        #create progression for losers Grand Final
        output.append({
                        "SourceID": current-1,
                        "TargetID": current,
                        })
        output.append({
                        "SourceID": source_to_losers,
                        "TargetID": current,
                        "Losers": True
                        })
        
        #create progression for Grand Final
        current += 1
        output.append({
                        "SourceID": current-1,
                        "TargetID": current,
                        })
        output.append({
                        "SourceID": source_to_losers,
                        "TargetID": current,
                        })
        
        #create progression for bracket reset
        current += 1
        output.append({
                        "SourceID": current-1,
                        "TargetID": current,
                        })
        output.append({
                        "SourceID": current-1,
                        "TargetID": current,
                        "Losers": True
                        })
    
    if leftover_players and double_elimination:

        #start by solving the case where leftover players is less than half required for a full round. ex ro17-24 or ro33-48
        if leftover_players<=number_of_qualfying_players/3:
            current = number_of_initial_lobbies
            for lobby in matchup_indexes[:leftover_players]:
                current += 1
                #advance leftover winners to main round
                output.append({
                                "SourceID": current,
                                "TargetID": lobby+1,
                                })
            
            #add leftover loser progressions
            current = number_of_initial_lobbies

            for lobby in matchup_indexes[:leftover_players]:
                current += 1
                #progress leftover player to leftover loser
                output.append({
                            "SourceID": current,
                            "TargetID": current+leftover_players,
                            "Losers": True
                            })
                #progress main round players to leftover losers
                output.append({
                            "SourceID": (number_of_qualfying_players-leftover_players)//2-lobby,
                            "TargetID": current+leftover_players,
                            "Losers": True
                            })
                #progress winner of leftover losers to main losers
                output.append({
                            "SourceID": current+leftover_players,
                            "TargetID": number_of_qualfying_players-leftover_players+lobby//2,
                            })

    return output

def get_progression_redemption(rounds: int, redemption_players: int, leftover_players: int, matchup_indexes: list, main_progression_size: int, double_elimination: bool) -> list:
    number_of_initial_lobbies = 2**rounds*2-1 #get number of main players. times two minus one includes the lobbies in losers bracket

    output = get_progression(rounds, redemption_players, number_of_initial_lobbies, matchup_indexes, leftover_players, double_elimination)

    #offset progressions to fit redemption bracket
    for progression in output:
        progression['SourceID'] += main_progression_size
        progression['TargetID'] += main_progression_size
    
    return output



#create bracket
def create_bracket(api: Ossapi, mp: list, number_of_qualifying_players: int, redemption_players: int, double_elimination: bool, seeding_method: str, manual_input: bool, teams_vs: bool, input_teams: dict) -> None:
    global counter
    global scores_dict
    global player_data
    global seeding

    #print to GUI terminal if an error is raised
    try:
        #rounds = floor(log(number_of_qualifying_players)/log(2))
        rounds = number_of_rounds(number_of_qualifying_players)
        rounds_list = ['Finals', 'Semi Finals', 'Quarter Finals', 'Round of 16', 'Round of 32', 'Round of 64', 'Round of 128'][:rounds]

        #write messages informing what the script is currently doing
        print('1/4: preparing..')
        GUI_terminal_print('1/4: preparing..')

        #use the first lobby ID to set standart values for the tournament
        map_list = get_map_list(api, mp[0])
        included_mods = get_included_mods(api, mp[0])
        mod_count = get_mod_count(api, mp[0], included_mods)
        
        #request scores
        print('2/4: requesting scores..')
        GUI_terminal_print('2/4: requesting scores..')
        delete_newline_character() #there was some annoying space idk why

        #write manual input scores
        scores_dict = {}
        if manual_input:
            manual_scores_input(mod_count, teams_vs)

        #request scores
        for lobby in mp:
            if script_terminating:
                raise ValueError("\nScript terminated")
            
            #print how many players have been loaded  
            counter += 1
            update_terminal_text(counter, len(mp))
            print(f'\r({counter}/{len(mp)})', end='', flush=True)

            #if a qualifier lobby is conducted incorrectly the script might break and raise an error message. Script will then open the error solver
            try:

                #request scores from a lobby
                if teams_vs:
                    new_lobby_scores = request_scores_teams(api, lobby, input_teams)
                else:
                    new_lobby_scores = request_scores(api, lobby)
                
                #raise expection if a player didn't play all maps
                for player in new_lobby_scores:
                    if len(new_lobby_scores[player])!=len(map_list):
                        raise Exception("Some players didn't play all maps")

            except Exception as e:
                #a lobby has been conducted incorrectly, now the script decides how to solve the issue
                print(f'An error has occurred in lobby {lobby}.')
                print('retrying..')
                new_lobby_scores = error_solver(api, lobby, mod_count, teams_vs, input_teams)
                print('---------------------------------')
                print('requesting scores..')
            
            #combine the scores from this lobby with the previous lobbies
            for score in new_lobby_scores:
                scores_dict[score] = new_lobby_scores[score]
        delete_lastline()

        #request player data
        print('3/4: requesting player data..')
        GUI_terminal_print('\n3/4: requesting player data..')
        delete_newline_character() #there was some annoying space idk why

        counter = 0
        player_data = {}
        number_of_players = len(scores_dict)
        if teams_vs:
            for team in input_teams:
                if script_terminating:
                    raise ValueError("\nScript terminated")
                
                if team in scores_dict: #ignore teams that didn't play qualifier
                    counter += 1
                    update_terminal_text(counter, number_of_players)
                    print(f'\r({counter}/{number_of_players})', end='', flush=True) #print how many players have been loaded            
                    for player in input_teams[team]:
                        player_data[player] = request_playerdata_teams(api, player)
        else:
            for player in scores_dict:
                if script_terminating:
                    raise ValueError("\nScript terminated")
                
                counter += 1
                update_terminal_text(counter, number_of_players)
                print(f'\r({counter}/{number_of_players})', end='', flush=True) #print how many players have been loaded      
                player_data[player] = request_playerdata(api.user(player))
        delete_lastline()
        print()

        #write the brack.json file
        print('4/4: writing bracket..')
        GUI_terminal_print('\n4/4: writing bracket..')
        scores_np = convert_scores_to_np(scores_dict)
        get_seeding(scores_np, seeding_method, len(map_list))

        #check for identical acronyms
        if teams_vs:
            teamnames = list(seeding[:, 0])
            acronyms = []
            dublicated_acronyms = []
            for teamname in teamnames: #find all dublicated acronyms
                acronym = teamname[:3].upper()
                if acronym in acronyms:
                    dublicated_acronyms.append(acronym)
                acronyms.append(acronym)
            seeding = np.hstack((np.array(acronyms).reshape(-1,1), seeding)) #store acronyms in seeding
            
            #solve dublicated acronyms
            if dublicated_acronyms != []:
                teams_with_dublicated_acronyms = []
                for teamname in teamnames:
                    if teamname[:3].upper() in dublicated_acronyms:
                        teams_with_dublicated_acronyms.append(teamnames.index(teamname))
                acronym_solver(teams_with_dublicated_acronyms, True)
        else: 
            acronyms = []
            dublicated_acronyms = []
            for player in player_data: #find all dublicated acronyms
                acronym = player_data[player]['acronym']
                if acronym in acronyms:
                    dublicated_acronyms.append(acronym)
                acronyms.append(acronym)
            
            #solve dublicated acronyms
            if dublicated_acronyms != []:
                players_with_dublicated_acronyms = []
                for player in player_data:
                    if player_data[player]['acronym'] in dublicated_acronyms:
                        players_with_dublicated_acronyms.append(player)
                acronym_solver(players_with_dublicated_acronyms, False)

        if teams_vs:
            teamsJSON = get_teams(scores_np, number_of_players, map_list, mod_count, included_mods, input_teams)
        else:
            teamsJSON = get_teams_1v1(scores_np, number_of_players, map_list, mod_count, included_mods)
        leftover_players = number_of_qualifying_players - (1 << (number_of_qualifying_players.bit_length()-1)) #find number of extra players
        matchesJSON, matchup_indexes = get_matches(seeding, rounds_list[-1], number_of_qualifying_players, leftover_players, double_elimination, teams_vs)
        progressionsJSON = get_progression(rounds, number_of_qualifying_players, len(matchesJSON)-leftover_players*2, matchup_indexes, leftover_players, double_elimination)
        roundsJSON = get_rounds(rounds_list, number_of_qualifying_players, leftover_players, len(matchesJSON), double_elimination)

        if redemption_players:
            rounds = int(log2(1 << (redemption_players.bit_length()-1))) #round down players to lowest power of two, then take log2 of that
            leftover_players = redemption_players-2**rounds #main players are rounds^2. Subtract that to get leftover players
            rounds_list = ['Finals', 'Semi Finals', 'Quarter Finals', 'Round of 16', 'Round of 32', 'Round of 64', 'Round of 128'][:rounds]
            main_bracket_size = len(matchesJSON)
            
            redemption_matches, matchup_indexes = get_matches(offset_seeding(seeding, number_of_qualifying_players), rounds_list[-1], number_of_qualifying_players, leftover_players, double_elimination, teams_vs)
            matchesJSON = merge_redemption_bracket(matchesJSON, redemption_matches, main_bracket_size)
            roundsJSON = merge_redemption_rounds(roundsJSON, rounds_list, redemption_players, leftover_players, len(matchesJSON)-main_bracket_size, main_bracket_size, double_elimination)
            progressionsJSON.extend(get_progression_redemption(rounds, redemption_players, leftover_players, matchup_indexes, main_bracket_size, double_elimination))

        data = {
        "Ruleset": {
            "ShortName": "osu",
            "Name": "osu!",
            "InstantiationInfo": "osu.Game.Rulesets.Osu.OsuRuleset, osu.Game.Rulesets.Osu",
            "LastAppliedDifficultyVersion": 20220902,
            "Available": True
        },
        "Matches": matchesJSON,
        "Rounds": roundsJSON,
        "Teams": teamsJSON,
        "Progressions": progressionsJSON,
        "ChromaKeyWidth": 1366,
        "PlayersPerTeam": 4,
        "AutoProgressScreens": True
        }
        
        with open('bracket.json', 'w') as file:
            json.dump(data, file, indent=2)
        write_data(teamsJSON, scores_np)

        GUI_terminal_print('Done!')
        enable_widgets(root)

    except Exception as e:
        GUI_terminal_print('error: '+str(e))
        enable_widgets(root)


#defining global variables
counter = 0
script_terminating = False
failed_lobby_data = {}
failed_lobby_score_input_boxes = {}
failed_lobby_player_list = []
manual_score_input_boxes = []
manual_player_input_boxes = []
scores_dict = {}
player_data = {}
seeding = np.array([])

#set appearance
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("Resources/lazer_bracket_generator_theme.json")

#create the main application window
outer_root = ctk.CTk()
outer_root.title("Lazer Bracket Generator")

acronym_warning_text = ctk.CTkLabel(outer_root) #another random global variable

#make main frame
outer_frame = ctk.CTkScrollableFrame(outer_root, fg_color="white")
outer_frame.pack(fill=tk.BOTH, expand=True)

#make frame for widgets
root = ctk.CTkFrame(outer_frame, fg_color="white")
root.pack(fill=tk.Y)

#set GUI parameters
GUI_xspacing = 5
GUI_yspacing = 5
subframes_indent = (30, 0)
title_yspace = (10, 0)
title_font = ('font3', 20)
help_font = ('font3', 11)
bold_font = ctk.CTkFont(weight='bold')

#set background
'''bg_image = ctk.CTkImage(light_image=Image.open("Resources/background.png"), dark_image=Image.open("Resources/background.png"), size=(800,500))

background = ctk.CTkLabel(outer_frame, image=bg_image)
background.place(relx=0.5, rely=0, anchor="n")'''

#make api title
api_title = ctk.CTkLabel(root, text="What's your API??", font=title_font)
api_title.pack(anchor='w')

#make api frame
api_frame = ctk.CTkFrame(root, border_width=2)
api_frame.pack(padx=subframes_indent, anchor='w')

#create label for client ID
client_ID_label = ctk.CTkLabel(api_frame, text="Enter your api client ID:")
client_ID_label.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create text box for client ID
client_ID_input_box = ctk.CTkEntry(api_frame, width=60, placeholder_text='12345', validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(5)), '%P'))
client_ID_input_box.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create label for client secret
client_secret_label = ctk.CTkLabel(api_frame, text="Enter your api client secret:")
client_secret_label.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create text box for client secret
client_secret_input_box = ctk.CTkEntry(api_frame, width=300, placeholder_text='abddefgHIJKLMNOpqR123456789rstuvwsyzAbCd', validate='key', validatecommand=(outer_root.register(non_digit_chararcter_limit_creator(40)), '%P'))
client_secret_input_box.pack(padx=(5,50), pady=(5,0), anchor='w')

#create advise for how to get api key
api_help_label = ctk.CTkLabel(api_frame, text="What's my api?", font=help_font, text_color='gray40')
api_help_label.pack(padx=GUI_xspacing, pady=3, anchor='w')
ToolTip(api_help_label, 'In your osu! account settings page under the OAuth section you can make a client.\nWrite a random name and a random URL e.g: “http://localhost:XXXX/”\nwhere you replace “XXXX” with a random 4 digit number greater than 1024')

#create rounds title
rounds_title = ctk.CTkLabel(root, text='Rounds and IDs', font=title_font)
rounds_title.pack(pady=title_yspace, anchor='w')

#create round/lobby ID frame
rounds_frame = ctk.CTkFrame(root)
rounds_frame.pack(padx=subframes_indent, anchor='w')

#create rounds input label
rounds_label = ctk.CTkLabel(rounds_frame, text="Enter number of qualifying players:")
rounds_label.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create rounds input box
rounds_input_box = ctk.CTkEntry(rounds_frame, width=45, placeholder_text='0', validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(3)), '%P'))
rounds_input_box.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create label for mps
mp_label = ctk.CTkLabel(rounds_frame, text="Enter qualifier match IDs:")
mp_label.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create a button to add an extra text box
add_lobby_button = ctk.CTkButton(rounds_frame, text="Add lobby", font=bold_font, command=add_lobby)
add_lobby_button.pack(padx=GUI_xspacing, pady=GUI_yspacing, anchor='w')

#create frame for lobby input boxes
lobby_input_box_frame = ctk.CTkFrame(root)
lobby_input_box_frame.pack(padx=subframes_indent, anchor='w')

#create match ID help
matchID_help_label = ctk.CTkLabel(root, text="Match ID?", font=help_font, text_color='gray40')
matchID_help_label.pack(padx=GUI_xspacing, pady=3, anchor='w')
ToolTip(matchID_help_label, 'The numbers on the back of the mp link https://osu.ppy.sh/community/matches/XXXXXXXXX')

make_splitpiece()

#create settings title
settings_title = ctk.CTkLabel(root, text='Any settings?', font=title_font)
settings_title.pack(pady=title_yspace, anchor='w')

#create checkbox frame
settings_frame = ctk.CTkFrame(root)
settings_frame.pack(padx=subframes_indent, anchor='w')

#create boolean variabels
#single elimination
single_elimination_var = tk.BooleanVar()
single_elimination_checkbox = ctk.CTkCheckBox(settings_frame, text="Single Elimination", variable=single_elimination_var)
single_elimination_checkbox.grid(padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#match for 3rd place #this is initially hidden
match_for_3rd_place_var = tk.BooleanVar()
match_for_3rd_place_checkbox = ctk.CTkCheckBox(settings_frame, text="Match for 3rd Place", variable=match_for_3rd_place_var)

#redemption bracket
redemption_var = tk.BooleanVar()
redemption_checkbox = ctk.CTkCheckBox(settings_frame, text="Redemption Bracket", variable=redemption_var)
redemption_checkbox.grid(padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#input box for number of players in redemptino bracket
redemption_inputbox = ctk.CTkEntry(settings_frame, width=45, placeholder_text='0', validate='key', validatecommand=(outer_root.register(entry_chararcter_limit_creator(3)), '%P'))

#create a checkbox for manual input
manual_scores_input_var = tk.BooleanVar()
manual_scores_input_checkbox = ctk.CTkCheckBox(settings_frame, text="Manual input scores", variable=manual_scores_input_var)
manual_scores_input_checkbox.grid(padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#create a checkbox for TeamVS
team_vs_var = tk.BooleanVar()
team_vs_checkbox = ctk.CTkCheckBox(settings_frame, text="TeamVS", variable=team_vs_var)
team_vs_checkbox.grid(padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#create a large text box with scrollbar
team_vs_input_box = ctk.CTkTextbox(settings_frame, height=100, width=400, border_width=5)

#create seeding method menu
seeding_method_label = ctk.CTkLabel(settings_frame, text="Seeding method")
seeding_method_label.grid(padx=GUI_xspacing, pady=(5,0), sticky='w')
seeding_methods = ["Total Score", "Average Rank", "Zipf's Law"]
seeding_method_menu = ctk.CTkComboBox(settings_frame, values=seeding_methods)
seeding_method_menu.grid(padx=GUI_xspacing, pady=(0,5), sticky='w')
seeding_method_menu.set("Total Score")

make_splitpiece()

#create execute title
execute_title = ctk.CTkLabel(root, text="You're all set! Press the button.", font=title_font)
execute_title.pack(pady=title_yspace, anchor='w')

#make execute frame
execute_frame = ctk.CTkFrame(root)
execute_frame.pack(padx=subframes_indent, anchor='w')

#create an execute button
execute_button = ctk.CTkButton(execute_frame, text="Execute Script", font=bold_font, command=execute)
execute_button.grid(row=0, column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#create a terminate button
terminate_button = ctk.CTkButton(execute_frame, text="Terminate Script", font=bold_font, state="disabled", command=terminate_script)
terminate_button.grid(row=0, column=1, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#create output text widget
terminal_text_widget = ctk.CTkTextbox(execute_frame, height=100, width=400, border_width=5)
terminal_text_widget.grid(row=1, column=0, columnspan=9, padx=GUI_xspacing, pady=GUI_yspacing) #high column span to bring execute and terminate buttons close to eachother
terminal_text_widget.configure(state="disabled")

#create remember checkbox
remember_var = tk.BooleanVar()
remember_checkbox = ctk.CTkCheckBox(execute_frame, text="Remember", variable=remember_var)
remember_checkbox.grid(row=2, column=0, padx=GUI_xspacing, pady=GUI_yspacing, sticky='w')

#create feedback label
feedback_title = ctk.CTkLabel(root, text='Is something annoying you? Tell me about it!', font=title_font)
feedback_title.pack(pady=title_yspace, anchor='w')

#create feedback frame
feedback_frame = ctk.CTkFrame(root)
feedback_frame.pack(padx=subframes_indent, anchor='w')

#create discord link button
discord_logo = ctk.CTkImage(light_image=Image.open('Resources/discord_logo.png'), size=(50, 40))

discord_button = ctk.CTkButton(feedback_frame, text='', width=50, image=discord_logo, command=lambda: webbrowser.open('https://discord.gg/qrnZsnhB'), fg_color="white", hover_color="grey95")
discord_button.pack(side="left")

#create github link button
github_logo = ctk.CTkImage(light_image=Image.open('Resources/github_logo.png'), size=(50, 40))

github_button = ctk.CTkButton(feedback_frame, text='', width=50, image=github_logo, command=lambda: webbrowser.open('https://github.com/MikkelCornelius/Lazer_bracket_generator/issues'), fg_color="white", hover_color="grey95")
github_button.pack(side="left")

###

#load saved settup
lobby_input_boxes = []
if exists('CFGs/configuration.cfg'):
    saved_data = {'Client_id': None,
                  'Client_secret': None,
                  'Rounds': None,
                  'Single_Elimination': None,
                  '3rd_place': None,
                  'Seed_method': None,
                  'Manual': None,
                  'TeamVS': None,
                   'Remember': None,
                   'Teams_list': None}
    
    with open('CFGs/configuration.cfg', 'r') as file:

        #compile CFG data in saved data dictionary
        for line in file:
            if line=='Teams_list =\n':
                saved_data['Teams_list'] = file.read()
                break
            if line!='\n':
                line = line.strip()

                #handle variables with no values assigned
                if line[-1]=='=':
                    saved_data[line[:-1].strip()] = ''
                
                #handle everything else
                else:
                    key, val = line.split('=')
                    saved_data[key.strip()] = val.strip()
    
    #edit GUI
    if saved_data['Client_id']!='':
        client_ID_input_box.delete(0, "end")
        client_ID_input_box.insert("end", saved_data['Client_id'])
    if saved_data['Client_secret']!='':
        client_secret_input_box.delete(0, "end")
        client_secret_input_box.insert("end", saved_data['Client_secret'])
    if saved_data['Rounds']!='':
        rounds_input_box.delete(0, "end")
        rounds_input_box.insert("end", saved_data['Rounds'])
    
    #lobbies
    if 'Lobby1' in saved_data:
        i = 1
        while f'Lobby{i}' in saved_data:
            if saved_data[f'Lobby{i}']!='' or i<=3:
                add_lobby()
                lobby_input_boxes[-1].insert("end", saved_data[f'Lobby{i}'])
            i += 1
    else:
        for i in range(3):
            add_lobby()

    #bools
    single_elimination_var.set(eval(saved_data['Single_Elimination']))
    match_for_3rd_place_var.set(eval(saved_data['3rd_place']))
    redemption_var.set(bool(saved_data['Redemption']))
    if redemption_var.get():
        redemption_inputbox.insert(0, saved_data['Redemption'])
    manual_scores_input_var.set(eval(saved_data['Manual']))
    team_vs_var.set(eval(saved_data['TeamVS']))
    remember_var.set(eval(saved_data['Remember']))

    #seeding method
    seeding_method_menu.set(saved_data['Seed_method'].replace('_', ' '))

    #teams
    team_vs_input_box.insert("end", saved_data['Teams_list'])
    
else:
    #create initial text boxes
    for i in range(3):
        add_lobby()
    
    #remember
    remember_var.set(True)

#set up widgets that can toggle to hide or show
single_elimination_var.trace_add('write', lambda *_: toggle_match_for_3rd_place())
team_vs_var.trace_add('write', lambda *_: toggle_team_vs())
redemption_var.trace_add('write', lambda *_: toggle_redemption())

#toggle hide/show if checkboxes were true in saved data
if single_elimination_var.get():
    toggle_match_for_3rd_place()
if team_vs_var.get():
    toggle_team_vs()
if redemption_var.get():
    toggle_redemption()

#set closing protocol
outer_root.protocol("WM_DELETE_WINDOW", on_closing)

#set window size
outer_root.geometry("650x600")

#start the GUI event loop
outer_root.mainloop()
