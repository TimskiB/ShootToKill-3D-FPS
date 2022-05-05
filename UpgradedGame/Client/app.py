import json
import socket
import sys
from random import randint
from threading import Thread
from time import sleep

from kivy.config import Config
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, get_color_from_hex
from kivy.uix.screenmanager import ShaderTransition
from kivymd.app import MDApp
from kivymd.icon_definitions import md_icons
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.list import IRightBodyTouch, TwoLineAvatarIconListItem, OneLineAvatarIconListItem, \
    OneLineIconListItem, ThreeLineIconListItem
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.taptargetview import MDTapTargetView
from kivymd_extensions.akivymd.uix.dialogs import AKAlertDialog

from app_client import Client


class LobbyPlayer(OneLineIconListItem):
    """Custom list item."""
    pass


class Lobby(ThreeLineIconListItem):
    """Custom list item."""
    pass


class CustomOneLineIconListItem(OneLineIconListItem):
    """Custom list item."""
    """This is the user that is showed in the search result"""
    pass


class ChatBubble(MDLabel):
    """The chat bubble represents a message in the chat screen"""
    send_by_user = BooleanProperty()


class ListItemWithOptions(OneLineAvatarIconListItem):
    """Custom list item"""
    """This list item represents the user in the home screen"""


class Options(IRightBodyTouch, MDBoxLayout):
    """Custom right container."""
    """The 2 icons in the right side of ListItemWithOptions"""


class MainApp(MDApp):
    username = "Tim"  # Debug username
    chat_logs = ListProperty()  # The data that is after words translated to chat messages

    # exec(open('Game/game.py').read())

    def build(self):
        """
        Initialize GUI amd set up graphics.
        :return:
        """

        self.title = "Shoot To Kill"
        self.icon = 'assets/images/icon.ico'

        Window.size = (450, 650)
        LabelBase.register(name='Lexend',
                           fn_regular='assets/fonts/Lexend-Regular.ttf')

        # App Variables
        self.online_users = {}
        self.online_users_widgets = []
        self.second_user = ""
        self.current_lobby_id = ""
        self.lobbies = {}
        self.lobbies_widgets = []
        self.open_lobbies = 0
        self.search_ready = False
        self.search_users = {}
        self.rejected = False

        return Builder.load_file('app.kv')  # We tell the app where is the design code

    def on_stop(self):
        """
        This function is run when user closes the window
        Here we close the threaded while loop because it stops the app from closing
        :return:
        """
        client.disconnect()
        self.t.join()

    def check_connection(self):
        """
        Notify the user if they are connected to the server or they can go offline without auth (DEBUG MODE)
        :return:
        """
        snackbar = Snackbar(
            text="error",
            snackbar_x="10dp",
            snackbar_y="10dp",
        )  # A bar pop up
        snackbar.size_hint_x = (
                                       Window.width - (snackbar.snackbar_x * 2)
                               ) / Window.width
        if offline:
            snackbar.text = "Failed to connect to the server."
            snackbar.buttons = [
                MDFlatButton(
                    text="GO OFFLINE",
                    text_color=(1, 1, 1, 1),
                    on_release=self.change_screen("home screen"),
                )]

        else:
            snackbar.text = "You are successfully connected to the server."
        snackbar.open()

    def change_screen(self, screen_name, curr=None, duration=0.4, title=None):
        """ Switch from screen to screen from backend and frontend """
        """There are multiple screens and the take up the whole screen"""
        self.root.ids.screen_manager.current = screen_name
        self.root.ids.screen_manager.duration = duration
        if curr is not None:
            self.root.ids.screen_manager.transition.direction = 'right'
        else:
            self.root.ids.screen_manager.transition.direction = 'left'
        if title is not None:
            self.set_title(title)

    def change_page(self, page_name, curr=None, title=None):
        """ Switch from screen to screen from backend and frontend """
        """There are only 2 pages: home screen, lobbies screen"""
        self.root.ids.page_manager.current = page_name  # Switch page
        if curr is not None:
            self.root.ids.page_manager.transition.direction = 'right'
        else:
            self.root.ids.page_manager.transition.direction = 'left'
        if title is not None:
            self.set_title(title)

    def success_registration(self, username: str):
        """
        Notify the user that his user is now registered
        :param username:
        :return:
        """
        dialog = AKAlertDialog(
            header_icon="check-circle-outline", header_bg=[0, 0.7, 0, 1]
        )
        content = Factory.SuccessDialog()
        content.ids.button.bind(on_release=lambda x: self.valid_auth(username, dialog))
        dialog.content_cls = content
        dialog.open()

    def register_user(self):
        """
        Register new info to the database
        :return:
        """
        username = self.root.ids.create_username.text
        password = self.root.ids.create_password.text
        if password == self.root.ids.confirm_password.text:
            register = client.register(username, password)
            if register == "valid":
                print("[+] User is now registered")
                self.success_registration(username)

                # self.valid_auth(username)
            elif register == "taken":
                Snackbar(
                    text=f"Username is taken. Maybe {username}{randint(10, 99)}?",
                    bg_color=error_color
                ).open()
            else:
                Snackbar(
                    text="Error Occurred. Try again later.",
                    bg_color=error_color
                ).open()
        else:
            Snackbar(
                text="Passwords do not match",
                bg_color=error_color
            ).open()

    def valid_auth(self, username, dialog=None):
        """
        This function is called when login or registration is valid and shall continue to chat app
        :param dialog: If we entered from a dialog, close it
        :param username: The username that was entered in the process
        :return:
        """
        if dialog is not None:
            dialog.dismiss()

        client.new_server("chat")  # Connect to a new server in order to receive chat service
        self.change_screen("home screen", None, 1.5)
        self.root.ids.user_header.text = f"Welcome {username}!"
        self.t = Thread(target=self.receive_updates)
        self.t.start()
        self.username = username
        self.root.ids.page_manager.transition = ShaderTransition()

        self.run_tutorial()  # Display the blue circles that explain what the icons do

    def receive_updates(self):
        """
        This function is the main connector between the back-end and the front-end
        every time we get something new in the back-end this function 'translates' it
        to the user in a graphic way
        :return:
        """
        while True:
            update = client.receive_updates()
            print(f"[*] Received from server: {update}")

            if update == "exit":  # Special case
                break

            try:
                # Divide the header to parts in order to organize the receiving and applying process
                header = update["header"]
            except TypeError:
                break
            category = header.split('/')[0]
            sub_category = header.split('/')[1]
            if category == "user":
                if sub_category == "new_user":
                    # A new user came online
                    self.add_online_user(update["username"], update["id"])
                if sub_category == "leaving_user":
                    # Someone has left the app
                    self.remove_online_user(update["username"])
            elif category == "chat":
                if sub_category == "get_chat":
                    # We received a chat log
                    self.chat_logs = []
                    self.second_user = update["id"]  # Remember who are we talking to
                    chat_messages = update["messages"]
                    for message in chat_messages:
                        if message != "":
                            if message["send_by_user"] == client.get_self_id():
                                self.chat_logs.append(
                                    {"text": message["text"], "send_by_user": True, "pos_hint": {"right": 1}}
                                )
                            else:
                                self.chat_logs.append(
                                    {"text": message["text"], "send_by_user": False, "pos_hint": {"left": 1}}
                                )
                elif sub_category == "receive_message":
                    # We received a message, Lets check if we are talking to this person right now
                    if self.second_user == update["id"]:
                        # If yes, show the message visually
                        self.chat_logs.append(
                            {"text": update["message"], "send_by_user": False, "pos_hint": {"left": 1}}
                        )
                    else:
                        self.message_notifier(self.get_username_by_id(update["id"]))
            elif category == "game":
                # Any game related update
                if sub_category == "receive_invite":
                    # Open a pop up with accept/reject options
                    user_id = update["id"]
                    self.show_game_invite(self.get_username_by_id(user_id), user_id)
                if sub_category == "start_game":
                    self.change_screen("home screen")
                    Snackbar(
                        text=f"Match is opening in a new window...",
                        bg_color=success_color
                    ).open()
                    # Open a new window for the game
                    Thread(target=client.start_game, args=(update["id"], update["match_id"],)).start()
                if sub_category == "invite_rejected":
                    self.change_screen("home screen", "back")
                    Snackbar(
                        text=f"""{self.get_username_by_id(update["id"])} rejected the invite...""",
                        size_hint_x=.4,
                        bg_color=error_color
                    ).open()

            elif category == "lobbies":
                # Everything related to the lobbies screen
                if sub_category == "new_lobby":
                    self.add_lobby(update["name"], update["max"], update["lobby_id"],
                                   update["user"], update["players"])
                elif sub_category == "player_join" or sub_category == "player_leave":
                    self.update_lobby(update["lobby_id"], update["username"], sub_category.split('_')[1])
            elif category == "utility":
                if sub_category == "badges":
                    self.root.ids.lobby_badge.badge_text = str(update["lobbies"])
                    self.root.ids.users_badge.badge_text = str(update["users"])
                elif sub_category == "users":
                    self.search_users = update["users"]
                    self.search_ready = True  # Allow searching users
        sys.exit()

    def message_notifier(self, username: str):
        """
        Show a notification for a new received message
        :param username: The user who sent the message
        :return:
        """
        dialog = AKAlertDialog(
            header_icon="bell",
            progress_interval=5,
            fixed_orientation="landscape",
            pos_hint={"right": 1, "y": 0.05},
            dialog_radius=0,
            opening_duration=2,
            size_landscape=["350dp", "70dp"],
            header_width_landscape="70dp",
        )
        dialog.bind(on_progress_finish=dialog.dismiss)
        content = Factory.MessageNotification()
        content.ids.from_who.text = f"New Message From {username}"
        content.ids.button.bind(on_release=lambda x: self.enter_chat(username, dialog))
        dialog.content_cls = content
        dialog.open()

    def add_online_user(self, username, user_id):
        """
        Add to our app (visually and technically) an online user
        :param username:
        :param user_id:
        :return:
        """
        self.root.ids.users_badge.badge_text = str(int(self.root.ids.users_badge.badge_text) + 1)
        self.online_users[username] = user_id  # Save info about that user
        widget = ListItemWithOptions(text=f"{username}")
        self.root.ids.online_users.add_widget(widget)
        self.online_users_widgets.append(widget)
        self.search_users[username] = user_id

    def remove_online_user(self, username):
        """
        Delete offline user

        :param username: His username
        :return:
        """
        self.root.ids.users_badge.badge_text = str(int(self.root.ids.users_badge.badge_text) - 1)
        for list_item in self.online_users_widgets:
            if list_item.text == username:
                self.root.ids.online_users.remove_widget(list_item)

        del self.online_users[username]
        del self.search_users[username]

    def enter_chat(self, username, dialog=None):
        """
        This function gets called  in order to receive all information about a specific chat
         and display everything for the user when he enters the screen.
        :param username: The username of the person we are going to talk to
        :param dialog: If we entered from a dialog, close it
        :return:
        """
        if dialog is not None:
            dialog.dismiss()
        client.get_chat_data(username)
        self.change_screen("chat screen")
        self.root.ids.chat_name.title = username  # Set the title for the chat screen

    def send_message(self, msg):
        client.send_chat_msg(msg, self.second_user)
        self.root.ids.field.text = ""
        self.chat_logs.append(
            {"text": msg, "send_by_user": True, "pos_hint": {"right": 1}}
        )

    def back_home_screen(self):
        self.change_screen("home screen", "back")
        self.chat_logs = []
        self.second_user = ""

    def perform_auth(self, username, password):
        """
        Function runs user auth and loads data for the rest of the app (if valid).
        :param username: user's username
        :param password: user's password
        :return:
        """

        print(f"[*] Performing authentication...")
        if client.auth(username, password):
            # User info is valid
            print("[+] Authentication successful")
            self.valid_auth(username)
        else:
            dialog = AKAlertDialog(
                header_icon="close-circle-outline", header_bg=[0.9, 0, 0, 1]
            )
            content = Factory.ErrorDialog()
            content.ids.error_button.bind(on_release=dialog.dismiss)
            dialog.content_cls = content
            dialog.open()

    def run_tutorial(self):
        """
        Show button explanation when first entering the main screen
        :return:
        """
        try:
            tap_target_view = MDTapTargetView(
                widget=self.root.ids.example_chat,
                title_text="Chat With People",
                title_text_size=dp(25),
                description_text="Plan games, discuss life and more...",
                description_text_size=dp(20),
                description_text_color=[1, 1, 1, 0.9],
                widget_position="right_top",
                cancelable=True,
                outer_radius=dp(166),
                stop_on_outer_touch=True,
                target_radius=dp(30)
            )
            tap_target_view.bind(on_close=lambda x: self.next_tutorial())
            tap_target_view.start()
        except AttributeError:
            print("[-] Couldn't play tutorial. Internal module error.")
        #

    def next_tutorial(self):
        try:
            tap_target_view = MDTapTargetView(
                widget=self.root.ids.example_invite,
                title_text="Invite to play",
                title_text_size=dp(25),
                description_text="Remember, SHOOT TO KILL!",
                description_text_size=dp(20),
                description_text_color=[1, 1, 1, 0.9],
                widget_position="right_top",
                cancelable=True,
                outer_radius=dp(166),
                stop_on_outer_touch=True,
                target_radius=dp(30),

            )
            tap_target_view.bind(on_close=lambda x: self.close_tutorial())
            tap_target_view.start()
        except Exception as e:
            print(f"[-] Couldn't play tutorial. Internal module error. {e}")

    def close_tutorial(self):
        self.root.ids.online_users.remove_widget(self.root.ids.example_user)

    def set_title(self, title):
        self.root.ids.toolbar_chat_screen.title = title

    def dialog_close(self, *args):
        self.dialog.dismiss(force=True)

    def confirm_invite(self, username):
        self.dialog = MDDialog(
            title=f"Invite {username} to a game?",
            buttons=[
                MDFlatButton(
                    text="No",
                    text_color=self.theme_cls.primary_color,
                    on_release=self.dialog_close
                ),
                MDFlatButton(
                    text="Yes",
                    text_color=self.theme_cls.primary_color,
                    on_release=lambda x: self.game_invite(username)

                ),
            ],
        )
        self.dialog.open()

    def show_game_invite(self, username, user_id):
        """
        When the user receive an invite they are given a prompt whether they
        want to enter into a duel
        :param username:
        :param user_id:
        :return:
        """
        dialog = AKAlertDialog(
            header_icon="exclamation",
            header_bg=[1, 0.75, 0, 1],
            progress_interval=10,
        )
        dialog.bind(on_progress_finish=lambda x: self.check_reject_invite(user_id, dialog))  # Reject invite
        content = Factory.GameNotification()
        content.ids.accept_invite.bind(on_release=lambda x: self.accept_invite(user_id, dialog))
        content.ids.reject_invite.bind(on_release=lambda x: self.reject_invite(user_id, dialog))
        content.ids.game_invite_name.text = f"Game Invite From {username}"
        # content.bind(on_release=dialog.dismiss)
        dialog.content_cls = content
        dialog.open()

    def get_id_by_username(self, username):
        """
        Small function that helps finding an ID of a person
        :param username:
        :return:
        """
        return self.online_users[username]

    def get_username_by_id(self, user_id):
        """
        Small function that helps finding a username of a person
        :return:
        """
        for username, an_id in self.online_users.items():
            if an_id == user_id:
                return username

    def game_invite(self, username, dialog=None):
        self.dialog_close()
        if dialog is not None:
            dialog.dismiss()
        client.game_invite(self.get_id_by_username(username))
        self.root.ids.three_dots.active = True
        self.root.ids.invite_name.title = f"Waiting for {username}'s response..."
        self.change_screen("invite screen")
        enemy_id = 123

    def accept_invite(self, user_id, dialog=None):

        if dialog != None:
            dialog.dismiss()
        # Snackbar(
        #     text=f"Creating match...",
        # ).open()
        self.root.ids.three_dots.active = False
        self.rejected = True
        client.accept_invite(user_id)

        self.change_screen("home screen")

    def reject_invite(self, user_id, dialog=None):
        if dialog is not None:
            dialog.dismiss()
        self.rejected = True
        client.reject_invite(user_id)
        Snackbar(
            text=f"Rejected invite...",
            size_hint_x=.4
        ).open()

    def create_lobby_screen(self):
        self.change_screen("create lobby screen")

    def create_new_lobby(self):
        Snackbar(
            text=f"Creating new lobby...",
        ).open()
        lobby_name = self.root.ids.lobby_input_name.text
        lobby_max_players = self.root.ids.max_input_players.text
        client.create_lobby(lobby_name, lobby_max_players)
        self.change_screen("home screen")

    def add_lobby(self, lobby_name, max_players, lobby_id, creator, players):
        self.root.ids.lobby_badge.badge_text = str(int(self.root.ids.lobby_badge.badge_text) + 1)
        self.lobbies[lobby_id] = {
            "name": lobby_name,
            "max": max_players,
            "creator": creator,
            "players": players
        }
        item = ThreeLineIconListItem(
            text=f"{lobby_name}",
            secondary_text=f"""Players: {len(self.lobbies[lobby_id]["players"])}/{max_players}""",
            tertiary_text="Map: Default",
            on_release=lambda x: self.lobby_info(lobby_id)
        )
        item.add_widget(MDIconButton(icon='account-group'))
        self.root.ids.lobbies_list.add_widget(
            item
        )
        self.lobbies_widgets.append(item)

    def lobby_info(self, lobby_id):
        """
        Prepare the screen that shows info about the lobby using
        the lobbies dict
        :param lobby_id: The key for the lobbies dict
        :return:
        """
        self.root.ids.join_button.disabled = False
        self.current_lobby_id = lobby_id
        self.root.ids.lobby_creator.text = f"""Creator: {self.lobbies[lobby_id]["creator"]}"""
        self.root.ids.lobby_name.title = self.lobbies[lobby_id]["name"]
        self.root.ids.limit.text = f"""Lobby Size: {len(self.lobbies[lobby_id]["players"])}/{int(self.lobbies[lobby_id]["max"])}"""
        self.root.ids.lobby_players.clear_widgets()  # Remove last record of players
        for username in self.lobbies[lobby_id]["players"]:
            item = OneLineIconListItem(
                text=f"{username}"
            )
            icon = MDIconButton(icon='account')
            item.add_widget(icon)

            self.root.ids.lobby_players.add_widget(
                item
            )
            item = None
        self.change_screen("lobby screen")

        if int(self.lobbies[lobby_id]["max"]) <= len(self.lobbies[lobby_id]["players"]):
            self.root.ids.join_button.disabled = True

    def join_lobby(self):
        self.change_screen("home screen")
        Snackbar(
            text=f"Match is opening in a new window...",
            bg_color=success_color
        ).open()
        # client.start_game(update["id"], update["match_id"])
        client.join_lobby(self.current_lobby_id)
        Thread(target=client.start_game, args=(self.lobbies[self.current_lobby_id]["creator"],
                                               self.current_lobby_id,
                                               )).start()

    def spectate_lobby(self):
        self.change_screen("home screen")
        Snackbar(
            text=f"Have fun spectating...",
            bg_color=success_color
        ).open()
        # client.start_game(update["id"], update["match_id"])
        Thread(target=client.start_game, args=(self.lobbies[self.current_lobby_id]["creator"],
                                               self.current_lobby_id, True,
                                               )).start()

    def update_lobby(self, lobby_id, username, action):
        """
        Update the players list of a specific lobby
        :param lobby_id:
        :param username:
        :param action:
        :return:
        """
        print(f"HEY SOMEONE IS {action}")
        if action == "join":
            self.lobbies[lobby_id]["players"].append(username)
            if self.current_lobby_id == lobby_id:  # If the lobby screen is currently open
                item = LobbyPlayer(text=f"username")

                self.root.ids.lobby_players.add_widget(
                    item
                )
            lobby_name = self.lobbies[lobby_id]["name"]
            for item_index in range(len(self.lobbies_widgets)):
                if self.lobbies_widgets[item_index].text == lobby_name:
                    self.root.ids.lobbies_list.remove_widget(self.lobbies_widgets[item_index])

                    self.lobbies_widgets.remove(self.lobbies_widgets[item_index])
                    item = Lobby(
                        text=f"{lobby_name}",
                        secondary_text=f"""Players: {len(self.lobbies[lobby_id]["players"])}/{self.lobbies[lobby_id]["max"]}""",
                        tertiary_text="Map: Default",
                        on_release=lambda x: self.lobby_info(lobby_id)
                    )

                    self.root.ids.lobbies_list.add_widget(
                        item, index=item_index
                    )
                    self.lobbies_widgets.insert(item_index, item)
                    break
        if action == "leave":
            self.lobbies[lobby_id]["players"].remove(username)
            if self.current_lobby_id == lobby_id:
                # Reload the lobby players
                self.root.ids.lobby_players.clear_widgets()
                for username in self.lobbies[lobby_id]["players"]:
                    item = LobbyPlayer(text=f"username")

                    self.root.ids.lobby_players.add_widget(
                        item
                    )
                    item = None

            # TODO: Upgrade, can be more efficient
            lobby_name = self.lobbies[lobby_id]["name"]
            for item_index in range(len(self.lobbies_widgets)):
                if self.lobbies_widgets[item_index].text == lobby_name:
                    self.root.ids.lobbies_list.remove_widget(self.lobbies_widgets[item_index])
                    self.lobbies_widgets.remove(self.lobbies_widgets[item_index])
                    item = ThreeLineIconListItem(
                        text=f"{lobby_name}",
                        secondary_text=f"""Players: {len(self.lobbies[lobby_id]["players"])}/{self.lobbies[lobby_id]["max"]}""",
                        tertiary_text="Map: Default",
                        on_release=lambda x: self.lobby_info(lobby_id)
                    )
                    item.add_widget(MDIconButton(icon='account-group'))
                    self.root.ids.lobbies_list.add_widget(
                        item, index=item_index
                    )
                    self.lobbies_widgets.insert(item_index, item)
                    break

    def enter_search_screen(self):
        self.change_screen("search screen")

    def set_list_users(self, text="", search=False):
        """Builds a list of icons for the screen MDIcons."""

        def add_user_item(username, user_id):
            self.root.ids.rv.data.append(
                {
                    "viewclass": "CustomOneLineIconListItem",
                    "text": username,
                    "on_release": lambda *x: self.show_user_info(username)
                    # "callback": lambda x: self.show_user_info(username)
                }
            )

        self.root.ids.rv.data = []
        for username in self.search_users.keys():
            if search:
                if text in username:
                    # Only users that include that in their name
                    add_user_item(username, self.search_users[username])
            else:
                # If nothing is typed, show all items
                add_user_item(username, self.search_users[username])

    def show_user_info(self, username):
        """
        Search result popup
        :param username:
        :return:
        """

        self.dialog = MDDialog(
            title="User Options",
            buttons=[
                MDFlatButton(
                    text="INVITE", text_color=self.theme_cls.primary_color,
                    on_release=lambda x: self.game_invite(username, self.dialog)
                ),
                MDFlatButton(
                    text="CHAT", text_color=self.theme_cls.primary_color,
                    on_release=lambda x: self.enter_chat(username, self.dialog)
                ),
            ],
        )

        self.dialog.open()

    def check_reject_invite(self, user_id, dialog):
        if not self.rejected:
            self.reject_invite(user_id)
        self.rejected = False


def get_addresses():
    info = json.load(open("servers_info.json"))["Address Server"]
    collector = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    collector.connect((info["ip"], int(info["port"])))
    data = collector.recv(2048).decode('utf8')
    left_bracket_index = data.index("{")
    right_bracket_index = data.rindex("}") + 1
    data = data[left_bracket_index:right_bracket_index]
    update = json.loads(data)

    with open("servers_info.json") as info:
        data = json.load(info)

    for server in data:
        # Update ip addresses
        if server != "Address Server":
            data[server]["ip"] = update[server]["ip"]
            data[server]["port"] = int(update[server]["port"])

    with open("servers_info.json", "w") as info:
        json.dump(data, info, indent=4, sort_keys=True)


def address_server():
    with open("servers_info.json") as info:
        data = json.load(info)

    data["Address Server"]["ip"] = input("Enter host: ")
    data["Address Server"]["port"] = int(input("Enter port: "))

    with open("servers_info.json", "w") as info:
        json.dump(data, info, indent=4, sort_keys=True)


if __name__ == "__main__":
    # Variables
    error_color = get_color_from_hex("e57373")
    success_color = get_color_from_hex("81c784")
    offline = False

    try:
        # address_server()
        # get_addresses()
        sleep(0.1)
        client = Client()
    except Exception as e:
        offline = True
        print(f"[-] Can't perform authentication, app is offline. ({e})")

    # Main App Execution
    #try:
    MainApp().run()
    # except Exception as e:
    #     print(f"[-] Shutting the app. ({e})")
