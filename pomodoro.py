#!/usr/bin/env python3
#-*-encoding:utf-8*-

WORK_COLOR = 92
PAUSE_COLOR = 93
BIG_PAUSE_COLOR = 94
LOG_COLOR = 95
LOGTIME_COLOR = 96

LOGS_HISTORY_MAX = 500

import os
import time
import argparse

class Pomodoro:
    def __init__(self, args):
        self.work = args.work
        self.pause = args.pause
        self.reps = args.reps
        self.big_pause = args.big_pause
        self.refresh_time = args.refresh

        self.secs_work = 0

        self.phase = 0
        self.phase_start = 0
        self.phase_time = 0.0
        self.end_phase_warning = False
        self.end_phase_warning_pct = 0.95 # TODO    Make configurable
        self.logs = list()

    def start(self):
        os.system("clear")
        self.log("Starting loop")
        try:
            while True:
                if self.update_phase():
                    self.end_phase()
                    self.phase += 1
                    self.start_phase()
                time.sleep(self.refresh_time)
        except KeyboardInterrupt:
            self.log("Interruption from user")
            if self.is_work_phase():
                self.secs_work += time.time() - self.phase_start
            print("\b\b{} mins were spent working, good job !".format(int(self.secs_work / 60)))

    def end_phase(self):
        if self.is_work_phase():
            self.secs_work += self.work

    def start_phase(self):
        self.end_phase_warning = False
        if self.is_work_phase():
            self.send_notification("Time to work !")
            self.log("Start work phase")
        elif self.is_pause_phase():
            self.send_notification("Time to take a short break !")
            self.log("Start pause phase")
        elif self.is_big_pause_phase():
            self.send_notification("Time to take a long break !")
            self.log("Start big pause phase")
        else:
            raise Exception("Phase not recognized")
        self.trigger_alarm()
        self.phase_start = time.time()

    def update_phase(self):
        if self.phase_start == 0:
            return True
        spent = time.time() - self.phase_start
        if self.is_work_phase():
            self.disp_screen(self.work, "WORK", WORK_COLOR)
            deadline = self.work
        elif self.is_pause_phase():
            self.disp_screen(self.pause, "PAUSE", PAUSE_COLOR)
            deadline = self.pause
        elif self.is_big_pause_phase():
            self.disp_screen(self.big_pause, "BIG PAUSE", BIG_PAUSE_COLOR)
            deadline = self.big_pause
        else:
            raise Exception("Phase not recognized")
        if not self.end_phase_warning and (spent / deadline > self.end_phase_warning_pct):
            self.trigger_end_phase_warning()
            self.end_phase_warning = True
        return spent > deadline

    def is_work_phase(self):
        return ((self.phase % (self.reps * 2)) % 2) == 1

    def is_pause_phase(self):
        return ((self.phase % (self.reps * 2)) % 2) == 0

    def is_big_pause_phase(self):
        return self.phase % (self.reps * 2) == 0

    def disp_screen(self, timer_max, name, color):
        termsize = os.get_terminal_size()
        secs_since_start = time.time() - self.phase_start
        print("\033[1;1H\033[2K", end="")
        add_secs_work = 0
        if self.is_work_phase():
            add_secs_work += secs_since_start
        print("Phase {}, {} mins of work done".format(self.phase, int((self.secs_work + add_secs_work)/ 60)))

        ncols = termsize.columns - len(name) - 4
        progress_bar = f"{name} ["
        progress_bar += "#" * ncols
        progress_bar += "]"

        print(f"\033[2K\033[{color}m{progress_bar}\033[0m")

        ndisp = termsize.lines - 2
        self.logs = self.logs[-LOGS_HISTORY_MAX:]
        for (logt, line) in self.logs[-ndisp:]:
            print(f"\033[2K\033[{LOGTIME_COLOR}m{logt}\t\033[{LOG_COLOR}m{line}\033[0m")

    # TODO
    def send_notification(self, message):
        pass

    def log(self, *args):
        self.logs.append((time.ctime(), " ".join(args)))

    def trigger_end_phase_warning(self):
        if self.is_work_phase():
            self.send_notification("Work phase soon finished, save your work !")
        elif self.is_pause_phase():
            self.send_notification("Pause soon finished, prepare to go back to work !")
        elif self.is_big_pause_phase():
            self.send_notification("Big pause soon finished, prepare to go back to work !")

    def trigger_alarm(self):
        # TODO  Trigger alarm sound, and wait for user input to start next phase
        print("\033[1;2H\033[2K", end="")
        input(" Press enter to start next phase ")

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", "-w", help="Work time to set", type=int, default=25*60)
    parser.add_argument("--pause", "-p", help="Break time to set", type=int, default=5*60)
    parser.add_argument("--reps", "-n", help="Repetitions before having a big pause", default=3)
    parser.add_argument("--big-pause", "-b", help="Big pause time to set", type=int, default=15*60)
    parser.add_argument("--refresh", "-r", help="Amount of time between refresh", type=float, default=0.5)
    return parser.parse_args()

def main():
    args = parse_args()
    pomodoro = Pomodoro(args)
    pomodoro.start()

if __name__ == "__main__":
    main()
