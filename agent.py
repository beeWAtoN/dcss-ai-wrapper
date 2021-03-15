from agents.rlagent import RLAgent
from gamestate import GameState
from actions import Command, Action
import subprocess
import random
import platform
import os
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib import style
import readchar
try:
    import msvcrt
except:
    pass

class Agent:
    def __init__(self):
        pass

    def get_action(self, gamestate: GameState):
        raise NotImplementedError()


class SimpleRandomAgent(Agent):
    """
    Agent that takes random cardinal actions to move/attack.
    """

    def do_sprint(self):
        # select sprint and character build
        return [{'msg': 'key', 'keycode': ord('a')},
                {'msg': 'key', 'keycode': ord('b')},
                {'msg': 'key', 'keycode': ord('h')},
                {'msg': 'key', 'keycode': ord('b')}
                ]

    def do_dungeon(self):
        # select dungeon and character build
        return [{'msg': 'key', 'keycode': ord('b')},
                {'msg': 'key', 'keycode': ord('i')},
                {'msg': 'key', 'keycode': ord('c')},
                ]

    def do_dungeon_webserver(self):
        # select dungeon and character build
        return [{'msg': 'input', 'text': 'b'},
                {'msg': 'input', 'text': 'i'},
                {'msg': 'input', 'text': 'c'},
                ]

    def get_game_mode_setup_actions(self):
        return self.do_dungeon()

    def get_game_mode_setup_actions_webserver(self):
        return self.do_dungeon_webserver()

    def get_action(self, gamestate):
        simple_commands = [Command.MOVE_OR_ATTACK_N,
                           Command.MOVE_OR_ATTACK_S,
                           Command.MOVE_OR_ATTACK_E,
                           Command.MOVE_OR_ATTACK_W,
                           Command.MOVE_OR_ATTACK_NE,
                           Command.MOVE_OR_ATTACK_NW,
                           Command.MOVE_OR_ATTACK_SW,
                           Command.MOVE_OR_ATTACK_SE]
        return random.choice(simple_commands)


class SimpleRLAgent:
    simple_commands = [Command.MOVE_OR_ATTACK_N,
                       Command.MOVE_OR_ATTACK_S,
                       Command.MOVE_OR_ATTACK_E,
                       Command.MOVE_OR_ATTACK_W,
                       Command.MOVE_OR_ATTACK_NE,
                       Command.MOVE_OR_ATTACK_NW,
                       Command.MOVE_OR_ATTACK_SW,
                       Command.MOVE_OR_ATTACK_SE]

    agent = RLAgent(actions=simple_commands)

    def get_action(self, gamestate):
        r = 2
        print("---------------------")
        print("Radius around agent (r={}):".format(r))
        num_rows = (2*r) + 1
        row_size = (2*r) + 1
        cell_vector = gamestate.get_cell_map().get_radius_around_agent_vector(r=2, tile_vector_repr='simple')
        agent_xy_vector = gamestate.get_cell_map().get_agent_xy_vector()

        string_ints = [str(i) for i in cell_vector]
        state = ''.join(string_ints)

        string_loc = [str(i) for i in agent_xy_vector]
        agent_loc = ''.join(string_loc)
        print(agent_loc)
        next_action = self.agent.run(agent_loc)
        # print(cell_vector)
        # for r in range(num_rows):
        #     s = ''
        #     for c in range(row_size):
        #         s += str(cell_vector[(r*row_size)+c])
        #     print(s)
        print("---------------------")
        print("action", next_action)
        return next_action


class TestAllCommandsAgent(Agent):
    """
    Agent that serves to test all commands are working. Cycles through commands in actions.Command enum.
    """

    def __init__(self):
        super().__init__()
        self.next_command_id = 1

    def do_dungeon(self):
        # select dungeon and character build
        return [{'msg': 'key', 'keycode': ord('b')},
                {'msg': 'key', 'keycode': ord('h')},
                {'msg': 'key', 'keycode': ord('b')},
                ]

    def get_game_mode_setup_actions(self):
        return self.do_dungeon()

    def get_action(self, gamestate):

        problematic_actions = [Command.REST_AND_LONG_WAIT,  # some kind of message delay issue
                               Command.WAIT_1_TURN,  # some kind of message delay issue
                               Command.FIND_ITEMS,  # gets stuck on a prompt
                               ]

        try:
            next_command = Command(self.next_command_id)
        except IndexError:
            self.next_command_id = 1
            next_command = Command(self.next_command_id)

        self.next_command_id += 1

        #  skip any known problematic actions for now
        while next_command in problematic_actions:
            next_command = self.get_action(gamestate)

        return next_command


class HumanInterfaceAgentDataTracking(Agent):

    def __init__(self):
        super().__init__()
        #plt.axis([-50, 50, 0, 10000])
        plt.ion()
        plt.show()

        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)

        self.gameturns = []
        self.num_game_facts = []

        self.state_facts_count_data = {}  # key is game turn, val is len(state_facts)
        self.number_of_monsters_data = {}  # key is game turn, val is number of monsters
        self.number_of_items_data = {}  # key is game turn, val is number of items seen in the game so far
        self.number_of_cells_data = {}  # key is game turn, val is number of cells seen in the game so far

    def get_action(self, gamestate):
        gameturn = gamestate.get_current_game_turn()
        num_facts = len(gamestate.get_all_pddl_facts())
        self.gameturns.append(gameturn)
        self.num_game_facts.append(num_facts)
        print("about to plot {}, {}".format(gameturn, num_facts))
        plt.plot(self.gameturns, self.num_game_facts)
        plt.draw()
        plt.pause(0.001)

        # linux solution:
        #next_action = readchar.readchar()

        # windows solution
        next_action = None
        while not next_action:
            try:
                next_action = msvcrt.getch().decode()
            except:
                print("Sorry, couldn't decode that keypress, try again?")
        next_action_command = Action.get_command_from_human_keypress(next_action)
        print("Got next_action {} and command is {}".format(next_action, next_action_command))
        return next_action_command


class FastDownwardPlanningAgent(Agent):
    """
    Agent that uses fast downward to solve planning problems to explore a floor.
    """

    pddl_domain_file = ""

    def __init__(self):
        super().__init__()
        self.current_game_state = None
        self.next_command_id = 1
        self.plan_domain_filename = "models/fastdownwardplanningagent_domain.pddl"
        self.plan_current_pddl_state_filename = "models/fdtempfiles/gamestate.pddl"
        self.plan_result_filename = "models/fdtempfiles/dcss_plan.sas"
        self.plan = []
        self.actions_taken_so_far = 0
        self.current_goal = None
        self.previous_goal = None
        self.previous_goal_type = None
        self.new_goal = None
        self.new_goal_type = None
        self.current_goal_type = None

    def do_dungeon(self):
        # select dungeon and character build
        return [{'msg': 'key', 'keycode': ord('b')},
                {'msg': 'key', 'keycode': ord('h')},
                {'msg': 'key', 'keycode': ord('b')},
                ]

    def do_dungeon_webserver(self):
        # select dungeon and character build
        return [{'msg': 'input', 'text': 'b'},
                {'msg': 'input', 'text': 'i'},
                {'msg': 'input', 'text': 'c'},
                ]

    def get_game_mode_setup_actions(self):
        return self.do_dungeon()

    def get_game_mode_setup_actions_webserver(self):
        return self.do_dungeon_webserver()

    def get_full_health_goal(self):
        return "(playerfullhealth)"

    def get_random_nonvisited_nonwall_playerat_goal(self):
        cells_not_visited = []
        cells_visited = []
        closed_door_cells = []
        for cell in self.current_game_state.get_cell_map().get_xy_to_cells_dict().values():
            if cell.has_player_visited:
                cells_visited.append(cell)
            elif not cell.has_wall and not cell.has_player and not cell.has_statue and not cell.has_lava and not cell.has_plant and not cell.has_tree and cell.g:
                # print("added {} as an available cell, it's g val is {}".format(cell.get_pddl_name(), cell.g))
                cells_not_visited.append(cell)
            else:
                pass

            if cell.has_closed_door:
                closed_door_cells.append(cell)

        # print("Found {} not visited cells".format(len(cells_not_visited)))
        i = 1
        farthest_away_cells = []
        target_cells = cells_not_visited
        while len(target_cells) > 1:
            farthest_away_cells = target_cells
            # remove all cells that are i distance away from other visited cells
            new_target_cells = []
            for potential_cell in target_cells:
                found_close_visited_cell = False
                for visited_cell in cells_visited:
                    if visited_cell.straight_line_distance(potential_cell) <= i:
                        found_close_visited_cell = True

                if not found_close_visited_cell:
                    new_target_cells.append(potential_cell)

            # print("  i={} with {} target cells".format(i, len(new_target_cells)))
            target_cells = new_target_cells
            i += 1

        #print("Found {} non visited cells {} distance away from player".format(len(farthest_away_cells), i - 1))

        if i < 4 and len(closed_door_cells) > 1:
            # print("Attempting to choose a closed door as a goal if possible")
            goal_cell = random.choice(closed_door_cells)
        elif len(farthest_away_cells) > 0:
            goal_cell = random.choice(farthest_away_cells)
            # print("Visited {} cells - Goal is now {}".format(len(cells_visited), goal_cell.get_pddl_name()))
        else:
            # can't find any cells
            return None

        goal_str = "(playerat {})".format(goal_cell.get_pddl_name())
        #print("Returning goal str of {}".format(goal_str))
        return goal_str

    def get_first_monster_goal(self):
        """
        This picks a the first available monster and chooses that monsters cell to be the goal. In the process of trying to move
        into the monsters cell, the agent should end up attacking the monster, because movement and attacking are the
        same thing (for melee).
        """
        cells_with_monsters = []
        for cell in self.current_game_state.get_cell_map().get_xy_to_cells_dict().values():
            if cell.monster:
                cells_with_monsters.append(cell)

        if len(cells_with_monsters) == 0:
            return None

        monster_cell_goal = random.choice(cells_with_monsters)
        monster_goal_str = "(not (hasmonster {}))".format(monster_cell_goal.get_pddl_name())
        #print("about to return monster goal: {}".format(monster_goal_str))
        # time.sleep(1)
        return monster_goal_str

    def get_plan_from_fast_downward(self, goals):
        # step 1: write state output so fastdownward can read it in
        if self.current_game_state:
            self.current_game_state.write_pddl_current_state_to_file(filename=self.plan_current_pddl_state_filename,
                                                                     goals=goals)
        else:
            print("WARNING current game state is null when trying to call fast downward planner")
            return []

        # step 2: run fastdownward
        # fast_downward_process_call = ["./FastDownward/fast-downward.py",
        #                               "--plan-file {}".format(self.plan_result_filename),
        #                               "{}".format(self.plan_domain_filename),
        #                               "{}".format(self.plan_current_pddl_state_filename),
        #                               "--search \"astar(lmcut())\""]
        # This is used for linux
        fast_downward_process_call = [
            "./FastDownward/fast-downward.py --plan-file {} {} {} --search \"astar(lmcut())\"".format(
                self.plan_result_filename,
                self.plan_domain_filename,
                self.plan_current_pddl_state_filename), ]
        # This is used for windows
        fast_downward_system_call = "python FastDownward/fast-downward.py --plan-file {} {} {} --search \"astar(lmcut())\" {}".format(
            self.plan_result_filename,
            self.plan_domain_filename,
            self.plan_current_pddl_state_filename,
            "> NUL")  # this last line is to remove output from showing up in the terminal, feel free to remove this if debugging

        # print("About to call fastdownward like:")
        # print(str(fast_downward_process_call))
        # print("platform is {}".format(platform.system()))
        if platform.system() == 'Windows':
            os.system(fast_downward_system_call)
        elif platform.system() == 'Linux':
            subprocess.run(fast_downward_process_call, shell=True, stdout=subprocess.DEVNULL)

        # step 3: read in the resulting plan
        plan = []
        try:
            with open(self.plan_result_filename, 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    if ';' not in line:
                        if line[0] == '(':
                            pddl_action_name = line.split()[0][1:]
                            command_name = pddl_action_name.upper()
                            plan.append(Command[command_name])
                    else:
                        # we have a comment, ignore
                        pass
        except FileNotFoundError:
            print("Plan could not be generated...")
            return []
        except:
            print("Unknown error preventing plan from being generated")
            return

        # for ps in plan:
        #    print("Plan step: {}".format(ps))

        return plan

    def equip_best_items(self):
        """
        Calling this will have the agent evaluate the best items
        """
        pass

    def read_scrolls(self):
        """
        The agent will read all scrolls in its inventory
        """
        pass

    def can_create_plan_to_reach_next_floor(self):
        """
        Returns a plan to go to the next floor
        """

        player_goal_str = None

        # first find a stair down
        cells_with_stairs_down = []
        for cell in self.current_game_state.get_cell_map().get_xy_to_cells_dict().values():
            if cell.has_stairs_down:
                cells_with_stairs_down.append(cell)

        # set the goal to be player at cell with stairs down
        if len(cells_with_stairs_down) > 0:
            player_goal_str = "(playerat {})".format(random.choice(cells_with_stairs_down).get_pddl_name())
        else:
            return False

        # create a plan to reach the stairs
        plan = self.get_plan_from_fast_downward(goals=[player_goal_str])

        # add an action to take the stairs down
        if plan and len(plan) > 0:
            plan.append(Command.TRAVEL_STAIRCASE_DOWN)

        return plan

    def goal_selection(self):
        """
        Returns the goal the agent should pursue right now

        In some cases, deciding to reach a goal may depend
        on whether that goal is even reachable via planning.
        Since we would have generated the plan anyway, let's
        return it and save some work
        """

        # attack monsters first
        monster_goal = self.get_first_monster_goal()
        if monster_goal:
            return monster_goal, "monster"
        #elif self.current_game_state.player_current_hp and self.current_game_state.player_hp_max and self.current_game_state.player_current_hp < self.current_game_state.player_hp_max / 2:
        #    return self.get_full_health_goal(), "heal"
        # elif self.actions_taken_so_far % 10 == 0 and random.random() < 0.25:
        #     # TODO - choose a lower depth for current branch of the dungeon
        #     lower_place_str = "{}_{}".format(self.current_game_state.player_place.lower().strip(),
        #                                      self.current_game_state.player_depth)
        #     return "(playerplace {})".format(lower_place_str), "stairsdown"
        else:
            goal = self.get_random_nonvisited_nonwall_playerat_goal()
            selected_goal = goal
            return selected_goal, "explore"

    def get_random_simple_action(self):
        simple_commands = [Command.MOVE_OR_ATTACK_N,
                           Command.MOVE_OR_ATTACK_S,
                           Command.MOVE_OR_ATTACK_E,
                           Command.MOVE_OR_ATTACK_W,
                           Command.MOVE_OR_ATTACK_NE,
                           Command.MOVE_OR_ATTACK_NW,
                           Command.MOVE_OR_ATTACK_SW,
                           Command.MOVE_OR_ATTACK_SE]
        return random.choice(simple_commands)

    def get_action(self, gamestate: GameState):
        self.current_game_state = gamestate

        self.new_goal, self.new_goal_type = self.goal_selection()
        print("Player at: {},{}".format(self.current_game_state.agent_x, self.current_game_state.agent_y))
        print("New goal: {} with type: {}".format(self.new_goal, self.new_goal_type))
        for a in self.plan:
            print("  plan action is {}".format(a))

        if self.new_goal and self.new_goal_type and (len(self.plan) < 1 or self.new_goal_type != self.previous_goal_type):
            self.current_goal = self.new_goal
            self.current_goal_type = self.new_goal_type
            # plan
            print("Planning with goal {}".format(self.new_goal))
            self.plan = self.get_plan_from_fast_downward(goals=[self.new_goal])
            self.previous_goal = self.new_goal
            self.previous_goal_type = self.new_goal_type

        next_action = None
        if self.plan and len(self.plan) > 0:
            next_action = self.plan.pop(0)
            self.actions_taken_so_far += 1
            return next_action

        print("warning - no plan, taking random action!")
        next_action = self.get_random_simple_action()
        return next_action
