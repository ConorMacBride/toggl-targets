#!/usr/bin/env python

# Load requirements
import numpy as np
from datetime import datetime, timezone, timedelta
import sys
import time
import requests
from urllib.parse import urlencode
from requests.auth import HTTPBasicAuth
import curses  # UNIX, MacOS

# Load config.csv

config_file = np.genfromtxt('config.csv', delimiter=',', skip_header=1, dtype=object)

API_TOKEN = config_file[0, 0].decode('utf-8')  # API token for Toggl
REFRESH_RATE = int(config_file[2, 0].decode('utf-8'))  # Number of 1 s to wait before getting new data from Toggl
TOGGL_ERROR = False  # Initialise error display variable
loops = 0  # Counter to determine when to refresh Toggl data

semester_data = np.array(config_file[:, 1:5], dtype='U')  # Columns SEMESTER to WORKLOAD
semester_data = semester_data[list(set(semester_data.nonzero()[0]))]
n_semesters = len(np.where(semester_data[:, 0] != '')[0])  # Number of semesters


def quantise_date(date):
    """
    Convert a datetime object into a UTC datetime object for the start of the day; defined as 3 AM of given day.
    :param date: datetime object
    :return: datetime object of start of given day in UTC
    """
    def to_datetime(date_string):
        return datetime.strptime(date_string, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)

    hour = int(date.strftime('%H'))
    if hour >= 3:  # In current day
        return to_datetime(date.strftime('%Y-%m-%d 03:00:00'))
    else:  # In previous day
        return to_datetime(date.strftime('%Y-%m-%d 03:00:00')) - timedelta(days=1)


GLOBAL_START_DATE = quantise_date(
    datetime.strptime(semester_data[0, 2], '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(hours=6)
)  # Start date of the first week with days starting at 3 AM
TIME_MACHINE = False  # Default to current time

if len(sys.argv) > 1:  # Parse time machine data from given arguments
    if sys.argv[1] == '-t':
        TIME_MACHINE = True
        try:  # Check that the date is valid
            TIME_MACHINE_DATE = datetime.strptime(sys.argv[2] + ' ' + sys.argv[3],
                                                  '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        except (ValueError, IndexError) as e:
            print("Invalid Time Machine Date. Required format: YYYY-MM-DD HH:MM:SS")
            sys.exit(1)


def current_time():
    """
    Determine the current time to be used in the program. A static current time can be defined at launch with '-t'.
    :return: datetime object
    """
    if TIME_MACHINE:
        return TIME_MACHINE_DATE
    else:
        return datetime.now(timezone.utc)


project_data = np.array(config_file[:, 5:9], dtype='U')  # Last 4 columns of config.csv
project_data = project_data[list(set(project_data.nonzero()[0]))]

TRACKED_TAGS = np.array(config_file[:5, 9:11], dtype='U')  # 5 tags max
TRACKED_TAGS = TRACKED_TAGS[list(set(TRACKED_TAGS.nonzero()[0]))]


def current_semester_data():
    """
    Get details of the current semester and week, and calculate workloads.
    :return: list of various values
    """
    progress = int(current_time().strftime('%s')) - int(GLOBAL_START_DATE.strftime('%s'))
    if progress <= 0:
        print("Year hasn't started yet. Try after " + GLOBAL_START_DATE.strftime('%Y-%m-%d %H:%M:%S'))
        sys.exit(0)

    n_weeks = int(np.floor(progress / (7 * 24 * 60 * 60)))  # Current week number -1

    current_week_date = GLOBAL_START_DATE + timedelta(weeks=n_weeks)  # Date of start of this week

    # Find when the semester starts
    semester_starts = np.where(semester_data[:, 0] != '')[0]
    semester_starts = int(max(semester_starts[semester_starts <= n_weeks]))
    semester_start_date = GLOBAL_START_DATE + timedelta(weeks=semester_starts)

    # Find when the semester ends
    semester_ends = np.where(semester_data[:, 0] != '')[0]
    try:
        semester_ends = int(min(semester_ends[semester_ends > n_weeks]))
    except ValueError:
        semester_ends = len(semester_data)
    semester_end_date = GLOBAL_START_DATE + timedelta(weeks=semester_ends)

    semester_name = semester_data[semester_starts][0]  # Name of semester
    week = semester_data[n_weeks, 1]  # Name of week

    # Fractional workload for week in semester
    semester_total_workload = float(sum(np.array(semester_data[semester_starts:semester_ends, 3], dtype=int)))
    semester_so_far_workload = float(sum(np.array(semester_data[semester_starts:n_weeks, 3], dtype=int)))
    week_workload = float(semester_data[n_weeks, 3])

    workload = week_workload / semester_total_workload  # Workload for current week
    cum_workload = semester_so_far_workload / semester_total_workload  # Cumulative workload for semester

    return semester_name, semester_start_date, semester_end_date, week, current_week_date, workload, cum_workload


# Save the values
CURRENT_SEMESTER, START_DATE, END_DATE, CURRENT_WEEK, \
    CURRENT_WEEK_START_DATE, CUR_WORKLOAD, CUM_WORKLOAD = current_semester_data()
CURRENT_WEEK_END_DATE = CURRENT_WEEK_START_DATE + timedelta(weeks=1)


def choose_tag(data):
    """
    Choose the first tag in data that appears in tracked tags.
    :param data: List of tags
    :return: string or None
    """
    for tag in data:
        if tag in TRACKED_TAGS[:, 0]:
            return tag
    return None


def query_toggl():
    """
    Get and process the relevant data from Toggl using the Toggl API.
    :return: numpy array of time entries
    """
    parameters = {'start_date': GLOBAL_START_DATE.isoformat(), 'end_date': current_time().isoformat()}
    url = 'https://www.toggl.com/api/v8/time_entries'
    if len(parameters) > 0:
        url = url + '?{}'.format(urlencode(parameters))

    headers = {'content-type': 'application/json'}
    r = requests.get(url, headers=headers, auth=HTTPBasicAuth(API_TOKEN, 'api_token'))
    r.raise_for_status()  # Check if there was an error

    entries = r.json()

    def format_date(date):  # Format the date in the format required by the Toggl API
        date_format = '%Y-%m-%dT%H:%M:%S%z'
        date = date[:-3]+date[-2:]
        return datetime.strptime(date, date_format)

    current_timer = 0
    for entry in entries:  # Go through each recorded entry
        try:  # Get the pid and semester of the module; and get tags
            module = np.where(project_data[:, 1].astype(int) == int(entry['pid']))[0]
            if len(module) != 0:  # If the entry's pid is in the defined list
                pid = int(entry['pid'])
                semester = project_data[module[0]][2]
            else:
                continue
        except KeyError:  # If the entry isn't part of a project
            continue

        try:  # try to get the main tag for the entry
            tag = choose_tag(entry['tags'])  # Choose the first tracked tag
        except KeyError:
            tag = None  # No tags set

        try:  # Try to get the time it was stopped
            stop = format_date(entry['stop'])
        except KeyError:
            current_timer = np.array([pid, semester, format_date(entry['start']), -1, -1, tag], dtype=object)
            continue
        if int(entry['duration']) >= 0:  # If the duration is positive it has stopped
            duration = int(entry['duration'])
        else:
            print("ERROR: Unexpected negative duration")  # Should not happen according to API docs.
            sys.exit(1)

        valid_entry = np.array([pid, semester, format_date(entry['start']), stop, duration, tag], dtype=object)
        try:
            table = np.append(table, [valid_entry], axis=0)
        except NameError:
            table = [valid_entry]

    try:  # Record the current timer
        if current_timer == 0:
            pass
    except ValueError:
        try:
            table = np.append(table, [current_timer], axis=0)
        except NameError:
            table = [current_timer]

    return table


def filter_semester(data, position=1):
    """
    Filter 'data' to only include time entries started in the current semester.
    :param data: data produced by query_toggl()
    :param position: position of the semester column (for flexibility)
    :return: filtered data
    """
    match_current_semester = np.where(data[:, position] == CURRENT_SEMESTER)[0]
    match_all_semesters = np.where(data[:, position] == "ALL")[0]
    return data[list(set(np.append(match_current_semester, match_all_semesters)))]


def filter_week(data):
    """
    Filter 'data' to only include time entries started in the current week.
    :param data: data produced by query_toggl()
    :return: filtered data
    """
    match_current_week_min = np.where(data[:, 2] >= CURRENT_WEEK_START_DATE)[0]
    match_current_week_max = np.where(data[:, 2] <= CURRENT_WEEK_END_DATE)[0]
    match_current_week = np.intersect1d(match_current_week_min, match_current_week_max)
    return data[match_current_week]


def filter_day(data):
    """
    Filter 'data' to only include time entries started in the current day.
    :param data: data produced by query_toggl()
    :return: filtered data
    """

    # Day starts at 3 am and continues to 3 am of the following day
    day_start = quantise_date(current_time())  # Enforce 3 AM rule
    day_end = day_start + timedelta(days=1)

    match_current_day_min = np.where(data[:, 2] >= day_start)[0]
    match_current_day_max = np.where(data[:, 2] <= day_end)[0]
    match_current_day = np.intersect1d(match_current_day_min, match_current_day_max)

    return data[match_current_day]


def group_projects(data, all_year=False):
    """
    Merge the query_toggl() data for each project to determine duration, and weekly and semester targets.
    :param data: data from query_toggl() (or its filters)
    :param all_year: boolean to determine if only all year modules are to be included
    :return: modified list of current projects from config file with additional columns
    """

    if all_year:  # Just give year-long details for semester="ALL" modules
        current_projects = project_data[project_data[:, 2] == "ALL"]
    else:
        current_projects = filter_semester(project_data, position=2)  # Data on the semester's projects

    n_projects = len(current_projects)  # Number of current projects
    n_tags = len(TRACKED_TAGS)  # Number of tracked tags
    durations = np.empty(n_projects, dtype=int)  # Holder for completed seconds for each project
    tags = np.empty((n_projects, n_tags), dtype=float)

    for i in range(n_projects):  # For each project
        pid = int(current_projects[i, 1])  # Get the project ID

        # Durations
        filtered_data = data[data[:, 0] == pid]  # Get time entries in "data" for this project
        durations[i] = np.sum(filtered_data[:, 4])  # Sum and record

        # Clean total hours and convert to seconds
        if current_projects[i, 2] == "ALL" and not all_year:
            # Number of hours to do THIS semester; assume work equally shared with each semester
            total_hours = float(current_projects[i, 3]) / float(n_semesters)
        else:
            total_hours = float(current_projects[i, 3])
        current_projects[i, 3] = int(total_hours * 60 * 60)  # Convert to whole seconds

        # Tags
        for j in range(n_tags):
            matched_tags = np.where(filtered_data[:, 5] == TRACKED_TAGS[j, 0])[0]  # Locations of entries with tag
            if durations[i] == 0:  # If no relevant entries found
                tags[i, j] = 0
            else:
                tags[i, j] = np.sum(filtered_data[matched_tags][:, 4]) / durations[i]  # Fraction of tot. project dur.

    # Number of seconds expected this week
    week_targets = current_projects[:, 3].astype(int) * CUR_WORKLOAD  # Ignore if all_year=True

    # Number of seconds expected so far this semester including all of current week
    semester_targets = current_projects[:, 3].astype(int) * CUM_WORKLOAD  # Ignore if all_year=True

    for new_col in [durations, week_targets, semester_targets]:  # Add the new data to the existing data
        current_projects = np.append(current_projects, new_col.reshape((current_projects.shape[0], 1)), 1)
    current_projects = np.append(current_projects, tags, 1)  # Add the tags
    return current_projects


def get_stats(data, mode):  # Processes group_projects() output
    """
    Get key statistics (target and/or completion progress) for given the time range.
    :param data: group_projects() output
    :param mode: time range: "day", "week", "semester" or "all"
    :return: target and completion progress, with overall figures
    """

    # Initialise
    target = None
    completion = None
    target_overall = None
    completion_overall = None

    # Get values for mode
    if mode == "day":
        target = data[:, 4].astype(float) / (data[:, 5].astype(float) / 7)  # done / daily target
        target_overall = np.sum(data[:, 4].astype(float)) / np.sum(data[:, 5].astype(float) / 7)
    elif mode == "week":
        target = data[:, 4].astype(float) / data[:, 5].astype(float)  # done / weekly target
        target_overall = np.sum(data[:, 4].astype(float)) / np.sum(data[:, 5].astype(float))
    elif mode == "semester":
        completion = data[:, 4].astype(float) / data[:, 3].astype(float)  # done / project total seconds
        completion_overall = np.sum(data[:, 4].astype(float)) / np.sum(data[:, 3].astype(float))
        target = data[:, 4].astype(float) / data[:, 6].astype(float)  # done / semester target progress
        target_overall = np.sum(data[:, 4].astype(float)) / np.sum(data[:, 6].astype(float))
    elif mode == "all":
        completion = data[:, 4].astype(float) / data[:, 3].astype(float)  # done / project total seconds
        completion_overall = np.sum(data[:, 4].astype(float)) / np.sum(data[:, 3].astype(float))

    return target, target_overall, completion, completion_overall


def format_time(seconds):
    """
    Convert number of seconds to hh:mm
    :param seconds: number of seconds
    :return: string
    """
    hours = float(seconds) / 60 / 60
    whole_hours = int(hours)
    whole_minutes = int((hours - whole_hours) * 60)
    if whole_hours < 0 or whole_minutes < 0:  # Deal with negative seconds
        if whole_hours < 0:
            minus = ''
        else:
            minus = '-'
        return minus + '{0:0>-2}'.format(whole_hours) + ':' + '{0:0>-2}'.format(-whole_minutes)
    else:
        return '{0:0>-2}'.format(whole_hours) + ':' + '{0:0>-2}'.format(whole_minutes)


# Start UNIX, MacOS output
stdscr = curses.initscr()
y = 0  # Initialise line counter


def print_nl(string, bold=False):
    """
    Print a new line to the terminal with curses
    :param string: string to print
    :param bold: activate bold formatting
    :return: nothing
    """
    global y, stdscr
    try:  # Don't go over the bottom
        if bold:  # Output bold text
            stdscr.addstr(y, 0, string, curses.A_BOLD)
        else:  # Output regular text
            stdscr.addstr(y, 0, string)
        y += 1  # Move cursor to next line
    except curses.error:
        height1, width1 = stdscr.getmaxyx()  # Update display size
        stdscr.addstr(height1-1, 0, str('...'))  # Alert


def print_reset():
    """
    Reset the curses screen for a new loop.
    :return: nothing
    """
    global y, stdscr, height, width, loops
    height, width = stdscr.getmaxyx()  # Display size
    status = '!' if TOGGL_ERROR else str(loops + 1)  # Determine the refresh status message
    stdscr.addstr(0, 0, status)
    stdscr.refresh()  # Refresh screen
    y = 0  # Start printing at top of screen
    stdscr.clear()  # Clear previous screen


def print_module_grid(data, heading, stat1=None, stat1_sum=None, stat2=None, stat2_sum=None, t="yearly"):
    """
    Print a table of data for each module. Calculates more key numbers and formats the output.
    :param data: list of module data
    :param heading: string for table heading
    :param stat1: list of decimals to be outputted as percentages
    :param stat1_sum: aggregate of stat1 list
    :param stat2: list of decimals to be outputted as percentages
    :param stat2_sum: aggregate of stat2 list
    :param t: type of target to be outputted: "daily", "weekly", "semester" or "yearly"
    :return:
    """
    total_duration = np.sum(data[:, 4].astype(float))  # Sum of durations

    if t == "daily":  # Use week target / 7
        targets = data[:, 5].astype(float) / 7
    elif t == "weekly":
        targets = data[:, 5].astype(float)
    elif t == "semester":
        targets = data[:, 6].astype(float)
    elif t == "yearly":  # Total seconds (hours) for module
        targets = data[:, 3].astype(float)
    total_targets = np.sum(targets)  # Sum of targets

    remaining = targets - data[:, 4].astype(float)
    total_remaining = total_targets - total_duration

    if width <= 40:  # Screen too narrow
        print_nl('|<' + '-' * (width - 4) + '>|')
        return 0

    if stat1 is not None and stat2 is not None:  # If two stats are given
        w = width - 40  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^6} {2:^6} {3:^8} {4:^8} {5:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1:>6} {2:>6} {3: 8.2%} {4: 8.2%} {5:>7}'  # Body format
        print_nl(head_fmt.format(heading[:w], '⏱', '🎯', '', '', '⏲'), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], format_time(data[module, 4]), format_time(targets[module]),
                     stat1[module], stat2[module], format_time(remaining[module])))
        print_nl(fmt.format("TOTAL"[:w], format_time(total_duration), format_time(total_targets),
                            stat1_sum, stat2_sum, format_time(total_remaining)), bold=True)  # Print aggregates
    elif stat1 is not None:  # If one stat is given
        w = width - 31  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^6} {2:^6} {3:^8} {4:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1:>6} {2:>6} {3: 8.2%} {4:>7}'  # Body format
        print_nl(head_fmt.format(heading[:w], '⏱', '🎯', '', '⏲'), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], format_time(data[module, 4]), format_time(targets[module]),
                     stat1[module], format_time(remaining[module])))
        print_nl(fmt.format("TOTAL"[:w], format_time(total_duration), format_time(total_targets),
                            stat1_sum, format_time(total_remaining)), bold=True)  # Print aggregates
    else:  # If no stats are given (Not currently in use.)
        w = width - 22  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^6} {2:^6} {3:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1:>6} {2:>6} {3:>7}'  # Body format
        print_nl(head_fmt.format(heading[:w], '⏱', '🎯', '⏲'), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], format_time(data[module, 4]), format_time(targets[module]),
                                format_time(remaining[module])))
        print_nl(fmt.format("TOTAL"[:w], format_time(total_duration), format_time(total_targets),
                            format_time(total_remaining)), bold=True)  # Print aggregates
    print_nl('')  # Insert blank line between tables


def print_tag_grid(data, toggl_data):
    """
    Print the table of tags for each project.
    :param data: project data
    :param toggl_data: query_toggl() data
    :return: nothing
    """

    # Find tag proportions across all projects
    total_duration = np.sum(data[:, 4].astype(float))  # Sum of durations
    n_tags = len(TRACKED_TAGS)
    tags = np.empty(n_tags, dtype=float)
    if total_duration == 0:  # If no relevant time entries found
        tags = 0
    else:
        for i in range(n_tags):
            matched_tags = np.where(toggl_data[:, 5] == TRACKED_TAGS[i, 0])[0]  # Locations of entries with tag
            tags[i] = np.sum(toggl_data[matched_tags][:, 4]) / total_duration  # Fraction of total duration

    if width <= 40:  # Screen too narrow
        print_nl('|<' + '-' * (width - 4) + '>|')
        return 0

    # Different formatting depending on number of tags tracked
    if n_tags == 5:
        w = width - 40  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^7} {2:^7} {3:^7} {4:^7} {5:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1: 7.2%} {2: 7.2%} {3: 7.2%} {4: 7.2%} {5: 7.2%}'  # Body format
        print_nl(head_fmt.format("Tracked Tags"[:w], TRACKED_TAGS[0, 1], TRACKED_TAGS[1, 1], TRACKED_TAGS[2, 1],
                                 TRACKED_TAGS[3, 1], TRACKED_TAGS[4, 1]), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], float(data[module, 7]), float(data[module, 8]),
                                float(data[module, 9]), float(data[module, 10]), float(data[module, 11])))
        print_nl(fmt.format("ALL"[:w], tags[0], tags[1], tags[2], tags[3], tags[4]), bold=True)  # Print aggregates
        print_nl('')
    elif n_tags == 4:
        w = width - 32  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^7} {2:^7} {3:^7} {4:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1: 7.2%} {2: 7.2%} {3: 7.2%} {4: 7.2%}'  # Body format
        print_nl(head_fmt.format("Tracked Tags"[:w], TRACKED_TAGS[0, 1], TRACKED_TAGS[1, 1],
                                 TRACKED_TAGS[2, 1], TRACKED_TAGS[3, 1]), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], float(data[module, 7]), float(data[module, 8]),
                                float(data[module, 9]), float(data[module, 10])))
        print_nl(fmt.format("ALL"[:w], tags[0], tags[1], tags[2], tags[3]), bold=True)  # Print aggregates
        print_nl('')
    elif n_tags == 3:
        w = width - 24  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^7} {2:^7} {3:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1: 7.2%} {2: 7.2%} {3: 7.2%}'  # Body format
        print_nl(head_fmt.format("Tracked Tags"[:w], TRACKED_TAGS[0, 1], TRACKED_TAGS[1, 1],
                                 TRACKED_TAGS[2, 1]), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], float(data[module, 7]), float(data[module, 8]),
                                float(data[module, 9])))
        print_nl(fmt.format("ALL"[:w], tags[0], tags[1], tags[2]), bold=True)  # Print aggregates
        print_nl('')
    elif n_tags == 2:
        w = width - 16  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^7} {2:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1: 7.2%} {2: 7.2%}'  # Body format
        print_nl(head_fmt.format("Tracked Tags"[:w], TRACKED_TAGS[0, 1], TRACKED_TAGS[1, 1]), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], float(data[module, 7]), float(data[module, 8])))
        print_nl(fmt.format("ALL"[:w], tags[0], tags[1]), bold=True)  # Print aggregates
        print_nl('')
    elif n_tags == 1:
        w = width - 8  # Maximum width
        head_fmt = '{0:>' + str(w) + '} {1:^7}'  # Heading format
        fmt = '{0:>' + str(w) + '} {1: 7.2%}'  # Body format
        print_nl(head_fmt.format("Tracked Tags"[:w], TRACKED_TAGS[0, 1]), bold=True)  # Print heading
        print_nl('─' * width)  # Print rule
        for module in range(len(data)):  # Print row for each module
            print_nl(fmt.format(data[module, 0][:w], float(data[module, 7])))
        print_nl(fmt.format("ALL"[:w], tags[0]), bold=True)  # Print aggregates
        print_nl('')


def set_running(data):
    """
    Update current duration for any timers in query_toggl() data that are still running.
    :param data: query_toggl() data
    :return: nothing
    """
    for running in np.where(data[:, 3] == -1)[0]:  # Will only be one (Zero if TIME_MACHINE)
        unix_start = int(data[running, 2].strftime('%s'))
        unix_end = int(datetime.now(timezone.utc).strftime('%s'))
        data[running, 4] = unix_end - unix_start  # Update duration


def main(stdscr):
    global TOGGL_ERROR, loops
    while True:
        print_reset()  # Start printing from the top of the screen
        if loops <= 0:
            try:
                year_toggl_data = query_toggl()  # Data for academic year
                TOGGL_ERROR = False
            except (requests.HTTPError, requests.ConnectionError) as e:  # HTTP or connection error encountered
                TOGGL_ERROR = True
                try:  # Check if previous local data exists
                    year_toggl_data
                except NameError:  # No previous data; keep trying Toggl
                    continue  # Restart while loop
                pass  # Use old data; try updating again later
            finally:
                loops = REFRESH_RATE  # Reset the refresh countdown

        # Main output goes here

        # Update duration for running timers
        set_running(year_toggl_data)

        # Filter time ranges
        semester_toggl_data = filter_semester(year_toggl_data)  # Data for semester
        week_toggl_data = filter_week(semester_toggl_data)  # Data for week
        day_toggl_data = filter_day(week_toggl_data)  # Data for day

        # Day Section
        projects = group_projects(day_toggl_data)
        target, target_overall, none1, none2 = get_stats(projects, mode="day")
        print_module_grid(projects, "Today", stat1=target, stat1_sum=target_overall, t="daily")

        # Week Section
        projects = group_projects(week_toggl_data)
        target, target_overall, none1, none2 = get_stats(projects, mode="week")
        print_module_grid(projects, CURRENT_WEEK, stat1=target, stat1_sum=target_overall, t="weekly")

        # Semester Section
        projects = group_projects(semester_toggl_data)
        target, target_overall, completion, completion_overall = get_stats(projects, mode="semester")
        print_module_grid(projects, CURRENT_SEMESTER,
                          stat1=target, stat1_sum=target_overall,
                          stat2=completion, stat2_sum=completion_overall, t="semester")

        # Tracked Tags
        print_tag_grid(projects, semester_toggl_data)

        # All Year Modules Section
        all_year_projects = group_projects(year_toggl_data, all_year=True)
        if len(all_year_projects) > 0:  # Only show table if there are all year modules
            none1, none2, completion, completion_overall = get_stats(all_year_projects, mode="all")
            print_module_grid(all_year_projects, "All Year Modules", stat1=completion, stat1_sum=completion_overall)

        if TIME_MACHINE:  # Freeze screen
            time.sleep(60 * 60)  # Quit after 1 hour
            sys.exit(0)

        loops -= 1  # Count down to refresh
        time.sleep(1)  # Update counter every 1 s


curses.wrapper(main)
