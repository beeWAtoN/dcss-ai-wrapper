try:
    import msvcrt
except:
    pass

from dcss.actions.command import Command
from dcss.agent.base import BaseAgent
from dcss.state.game import GameState
from dcss.actions.action import Action
from dcss.actions.menuchoice import MenuChoice
from dcss.state.menu import Menu
from dcss.state.monster import Monster

from dcss.websockgame import WebSockGame
from dcss.connection.config import WebserverConfig

import logging
logging.basicConfig(level=logging.WARNING)


class HumanInterfaceBaseAgentDataTracking(BaseAgent):

    def __init__(self):
        super().__init__()
        self.gamestate = None
        #plt.axis([-50, 50, 0, 10000])
        #plt.ion()
        #plt.show()

        #self.fig = plt.figure()
        #self.ax1 = self.fig.add_subplot(1,1,1)

        self.gameturns = []
        self.num_game_facts = []

        self.state_facts_count_data = {}  # key is game turn, val is len(state_facts)
        self.number_of_monsters_data = {}  # key is game turn, val is number of monsters
        self.number_of_items_data = {}  # key is game turn, val is number of items seen in the game so far
        self.number_of_cells_data = {}  # key is game turn, val is number of cells seen in the game so far

        self.nearby_monster = False

    def check_for_monsters(self):
        """
        Returns true if one or more nearby monsters
        """
        print("all monsters are: {}".format(Monster.ids_to_monsters))
        for monster_id in Monster.ids_to_monsters.keys():
            print("  monster {} has cell {}".format(monster_id, Monster.ids_to_monsters[monster_id].cell))
        self.nearby_monster = False
        for cell in self.gamestate.get_cell_map().get_xy_to_cells_dict().values():
            if cell.monster:
                print("cell.monster = {}".format(cell.monster))
                self.nearby_monster = True

    def get_action(self, gamestate: GameState):
        self.gamestate = gamestate
        #self.print_player_stats_vector(verbose=True)
        gameturn = gamestate.get_current_game_turn()
        num_facts = len(gamestate.all_pddl_facts())
        self.gameturns.append(gameturn)
        #self.print_all_items_near_player(gamestate)
        self.num_game_facts.append(num_facts)
        #print("about to plot {}, {}".format(gameturn, num_facts))
        #plt.plot(self.gameturns, self.num_game_facts)
        #plt.draw()
        #plt.pause(0.001)

        # linux solution:
        #next_action = readchar.readchar()

        # windows solution
        #next_action = None
        self.check_for_monsters()
        print("is there a monster nearby? {}".format(self.nearby_monster))
        print("Waiting for your next keypress, human")
        next_action = msvcrt.getch().decode()
        #next_action = input("Waiting for your next keypress, human")
        # while not next_action:
        #     try:
        #         next_action = msvcrt.getch().decode()
        #     except:
        #         print("Sorry, couldn't decode that keypress, try again?")
        next_action_command = self.get_command_from_human_keypress(next_action)
        print("Got next_action {} and command is {}".format(next_action, next_action_command))
        return next_action_command

    def print_all_items_near_player(self, gamestate: GameState, r=1):
        cells = gamestate.get_cell_map().get_radius_around_agent_cells(r=r)
        for cell in cells: # type: Cell
            for pddl_fact in cell.get_pddl_facts():
                print("{}".format(pddl_fact))

    def print_player_stats_vector(self, verbose=False):
        """
            Print the player stats vector
        """
        player_stats_vector = self.gamestate.get_player_stats_vector(verbose=verbose)
        print(player_stats_vector)
        print("Player stats vector has length {}".format(len(player_stats_vector)))


    def get_command_from_human_keypress(self, keypress):
        """
        Return the command that matches the keypress from the user
        """
        keypress_to_command_no_menu = {
            '1': Command.MOVE_OR_ATTACK_SW,
            '2': Command.MOVE_OR_ATTACK_S,
            '3': Command.MOVE_OR_ATTACK_SE,
            '4': Command.MOVE_OR_ATTACK_W,
            '5': Command.REST_AND_LONG_WAIT,
            '6': Command.MOVE_OR_ATTACK_E,
            '7': Command.MOVE_OR_ATTACK_NW,
            '8': Command.MOVE_OR_ATTACK_N,
            '9': Command.MOVE_OR_ATTACK_NE,
            'o': Command.AUTO_EXPLORE,
            '\t': Command.AUTO_FIGHT,
            'i': Command.SHOW_INVENTORY_LIST,
            '>': Command.TRAVEL_STAIRCASE_DOWN,
            '<': Command.TRAVEL_STAIRCASE_UP,
            '\r': Command.ENTER_KEY,
            'g': Command.PICKUP_ITEM,
            ',': Command.PICKUP_ITEM,
            '.': Command.WAIT_1_TURN,
            '%': Command.CHARACTER_OVERVIEW,
            '@': Command.DISPLAY_CHARACTER_STATUS,
            'A': Command.SHOW_ABILITIES_AND_MUTATIONS,
            '\x1b': Command.EXIT_MENU,
            'a': Command.USE_SPECIAL_ABILITY,
            'q': Command.QUAFF,
            'I': Command.LIST_ALL_SPELLS,
            'm': Command.SHOW_SKILL_SCREEN,
        }

        if self.gamestate.get_current_menu() is Menu.NO_MENU:
            return keypress_to_command_no_menu[keypress]
        elif keypress in Action.dcss_menu_chars:
            dcss_menu_char_i = Action.dcss_menu_chars.index(keypress)
            menuchoice = MenuChoice(dcss_menu_char_i)
            return menuchoice
        else:
            print("Got keypress {} and current Menu is {}".format(keypress, self.gamestate.get_current_menu()))
            return Command.EXIT_MENU


if __name__ == "__main__":
    my_config = WebserverConfig

    # set game mode to Tutorial #1
    my_config.game_id = 'dcss-web-trunk'
    my_config.always_start_new_game = True
    my_config.auto_start_new_game = True
    my_config.species = 'Vampire'
    my_config.background = 'Necromancer'

    # create game
    game = WebSockGame(config=my_config, agent_class=HumanInterfaceBaseAgentDataTracking)
    game.run()