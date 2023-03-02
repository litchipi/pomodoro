#!/usr/bin/env python3
#-*-encoding:utf-8*-

import os
import sys
import time
import argparse
import traceback
import threading
import subprocess
import simpleaudio
import dbus

DBUS_OBJ = dbus.SessionBus().get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
DBUS_OBJ = dbus.Interface(DBUS_OBJ, "org.freedesktop.Notifications")

ASSETS_DIR=os.path.dirname(os.path.abspath(__file__))
NOTIFY_SOUND=os.path.join(ASSETS_DIR, "notify.wav")
ALARM_SOUND=os.path.join(ASSETS_DIR, "alarm.wav")

WORK_COLOR = 92
PAUSE_COLOR = 93
BIG_PAUSE_COLOR = 94
LOG_COLOR = 95
LOGTIME_COLOR = 96

LOGS_HISTORY_MAX = 500

PROGRESS_CHARS = ["▐", "█", "░", "▌"]

DEFAULT_TIMES = {
    "work": 25,
    "pause": 5,
    "big_pause": 30,
}

def playsound(file, wait=False):
    wave_obj = simpleaudio.WaveObject.from_wave_file(file)
    play_obj = wave_obj.play()
    if wait:
        play_obj.wait_done()

def alarm_loop(evt):
    while not evt.is_set():
        playsound(ALARM_SOUND, wait=True)

class Pomodoro:
    def __init__(self, args):
        # Convert the times to seconds
        self.work = args.work * 60
        self.pause = args.pause * 60
        self.big_pause = args.big_pause * 60
        self.reps = args.reps
        self.refresh_time = args.refresh
        self.debug = args.debug
        self.phase = args.phase

        self.secs_work = 0

        self.init = True
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
                if self.init or self.update_phase():
                    if not self.init:
                        self.end_phase()
                    self.phase += 1
                    self.start_phase()
                    self.init = False
                time.sleep(self.refresh_time)
        except KeyboardInterrupt:
            self.log("Interruption from user")
            if self.is_work_phase():
                self.secs_work += time.time() - self.phase_start
            print("\b\b{} mins were spent working, good job !".format(int(self.secs_work / 60)))
            sys.exit(0)
        except Exception as err:
            print("Exception occured, printing all logs we have...")
            for (logt, line) in self.logs:
                print(f"{logt} - {line}")
            print("")
            traceback.print_exc()
            sys.exit(1)

    def end_phase(self):
        if self.is_work_phase():
            self.secs_work += self.work
        if self.is_work_phase():
            self.send_notification("Work is finished, take a break now")
        elif self.is_pause_phase():
            self.send_notification("Pause is finished, let's go back to work now")
        elif self.is_big_pause_phase():
            self.send_notification("Big pause is finished, let's go back to work now")
        self.trigger_alarm()

    def start_phase(self):
        self.end_phase_warning = False
        self.log(f"Start phase {self.phase}")
        self.phase_start = time.time()

    def update_phase(self):
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
        if not self.end_phase_warning and ((spent / deadline) > self.end_phase_warning_pct):
            self.log("Triggering end of phase warning")
            self.trigger_end_phase_warning()
            self.end_phase_warning = True
        return spent > deadline

    def is_work_phase(self):
        return ((self.phase % (self.reps * 2)) % 2) == 1

    def is_pause_phase(self):
        return (((self.phase % (self.reps * 2)) % 2) == 0) and (not self.is_big_pause_phase())

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
        progress = int((secs_since_start / timer_max) * ncols)
        progress_bar = f"{name} {PROGRESS_CHARS[0]}"
        progress_bar += (PROGRESS_CHARS[1] * progress) + (PROGRESS_CHARS[2] * (ncols-progress))
        progress_bar += PROGRESS_CHARS[3]

        print(f"\033[2K\033[{color}m{progress_bar}\033[0m")

        if self.debug:
            ndisp = termsize.lines - 2
            self.logs = self.logs[-LOGS_HISTORY_MAX:]
            for (logt, line) in self.logs[-ndisp:]:
                print(f"\033[2K\033[{LOGTIME_COLOR}m{logt}\t\033[{LOG_COLOR}m{line}\033[0m")

    def send_notification(self, message):
        playsound(NOTIFY_SOUND)
        DBUS_OBJ.Notify(
            "Pomodoro",
            0,
            os.path.join(ASSETS_DIR, "icon.png"),
            message, message,
            [],
            {"urgency": 1},
            10000
        )

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
        os.system("clear")
        stop_alarm = threading.Event()
        alarm_thread = threading.Thread(target=alarm_loop, args=(stop_alarm,))
        alarm_thread.start()
        input(" Press enter to start next phase ")
        stop_alarm.set()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", "-w", help="Work time to set (in mins)", type=int, default=DEFAULT_TIMES["work"])
    parser.add_argument("--pause", "-p", help="Break time to set (in mins)", type=int, default=DEFAULT_TIMES["pause"])
    parser.add_argument("--big-pause", "-b", help="Big pause time to set (in mins)", type=int, default=DEFAULT_TIMES["big_pause"])
    parser.add_argument("--reps", "-n", help="Repetitions before having a big pause", type=int, default=3)

    parser.add_argument("--refresh", "-r", help="Amount of time between refresh (in secs)", type=float, default=0.5)
    parser.add_argument("--debug", "-d", help="Enable debug logs in the screen output", action="store_true")
    parser.add_argument("--phase", help="Start directly to the given phase number", type=int, default=0)

    return parser.parse_args()

def main():
    args = parse_args()
    pomodoro = Pomodoro(args)
    pomodoro.start()

if __name__ == "__main__":
    main()
