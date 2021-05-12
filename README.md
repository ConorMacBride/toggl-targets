# Targets
*Track daily, weekly and seasonally project completion targets in real time.*

This program is designed to allow you to keep track of time spent in university courses. Track a subset of your Toggl projects; one for each module. This program lets you assign each of these modules to a semester (or all semesters) and state the number of hours you should spend on each module this year.

You can also define each week of the year and separate them into semesters. You can choose a custom name for each week and semester to be shown by this program. Some weeks won't be as busy as others so you can set a workload for each week also. This will update your daily and weekly targets accordingly.

Up to 5 Toggl tags can be tracked by the program. For each module and overall, see the proportion of your time that is spent in lectures, in tutorials, studying and more.

Days start and end at 3 AM so you can meet your daily targets into the night. You can also travel back in time and view historical data; just make sure you don't travel to a time when a tracked timer was currently running!

Download now at: <a href="https://github.com/ConorMacBride/toggl-targets">https://github.com/ConorMacBride/toggl-targets</a>

## Sample output

```
2                         Today   ⏱      🎯                ⏲
──────────────────────────────────────────────────────────────
                       Calculus  01:40  01:00  166.67%  -00:40
                Quantum Physics  02:10  01:00  216.67%  -01:10
              Organic Chemistry  00:30  00:30  100.00%   00:00
                   Group Theory  01:00  00:30  200.00%  -00:30
                  Final Project  00:20  01:00   33.33%   00:40
                          TOTAL  05:40  04:00  141.67%  -01:40

                         Week 2   ⏱      🎯                ⏲
──────────────────────────────────────────────────────────────
                       Calculus  04:32  07:00   64.76%   02:28
                Quantum Physics  03:12  07:00   45.71%   03:48
              Organic Chemistry  01:10  03:30   33.33%   02:20
                   Group Theory  04:05  03:30  116.67%  -00:35
                  Final Project  03:45  07:00   53.57%   03:15
                          TOTAL  16:44  28:00   24.31%   11:16

            Semester 1   ⏱      🎯                         ⏲
──────────────────────────────────────────────────────────────
              Calculus  09:45  12:00   81.25%   21.17%   02:15
       Quantum Physics  08:56  12:00   74.44%    5.96%   03:04
     Organic Chemistry  04:05  06:00   68.06%    0.00%   01:55
          Group Theory  07:10  06:00  119.44%    0.00%  -01:10
         Final Project  10:10  12:00   84.72%    0.00%   01:50
                 TOTAL  40:06  48:00   60.53%    6.26%   07:54

          Tracked Tags  Tut.    Lec.    Rev.    Dis.    Sum.
──────────────────────────────────────────────────────────────
              Calculus  30.00%  10.00%  20.00%  30.00%   0.00%
       Quantum Physics  44.00%  20.00%  26.00%   7.00%   3.00%
     Organic Chemistry   0.00%  35.00%  25.00%  30.00%   0.00%
          Group Theory  20.00%  20.00%  30.00%   0.00%   0.00%
         Final Project   0.00%   0.00%   0.00%  10.00%  40.00%
                   ALL  30.00%  20.00%  25.00%  20.00%   1.00%

               All Year Modules   ⏱      🎯                ⏲
──────────────────────────────────────────────────────────────
                  Final Project  10:10 400:00    2.54%  389:50
                          TOTAL  10:10 400:00    2.54%  389:50
```

## Program explained
The first block, 'Today', contains data on the tracked project with a start date in today. Days start and end at 3 AM. The second block contains data started within the current 7 calendar day block starting on the date defined in `config.csv`. The third block contains data for all the semester. The fourth block contains data on the tags that are being tracked and the last block contains all year data on modules that occur over all semesters.

The ⏱ column gives the time tracked (`HH:MM`) in the current period for each module. The 🎯 column gives the target number of hours (HH:MM) to track in this time period, except the semester block which is the target number of hours for all weeks so far this semester including the current week. The first percentage in the first three blocks is the percentage of this target that has been met. The second percentage in the semester block (and the last block) is the percentage of the project's total hours that has been completed. For the semester block, the total hours is divided by the number of semesters if it is an all year project. The ⏲ column is the amount of time remaining (`HH:MM`) until the target has been met.

The second last block gives data on the tracked tags. The tags are in the columns and the projects are in the rows. The percentages represent the percentage of all time tracked that have the corresponding tag. For this reason, the rows may not add up to 100% is all time entries were not assigned tracked tags.

If no tags are tracked or no all year projects are tracked, these blocks will not be shown. The tables will auto fit to the terminal window. `...` will appear in the bottom left corner if tables below have been cut. A number will count down in the top left corner to the time the local data will be refreshed over the internet. If there is an error refreshing, an `!` will be shown instead and it will try again in the next `REFRESH_RATE`.

## Install

### Download files
Download `targets.py`, `config.csv` and `projects.py` to your computer from the repository at <a href="https://github.com/ConorMacBride/toggl-targets">https://github.com/ConorMacBride/toggl-targets</a>. Make sure `targets.py` and `config.csv` are kept in the same folder.

### Setup configuration file
Next edit `config.csv` with your own data. Your own API token can be found at `https://track.toggl.com/profile`. This allows this program to access your Toggl data. The refresh rate can also be changed. This is how often the local data is updated.

The next four columns from `SEMESTER NAME` to `WORKLOAD` form the next block of data. Each row represents a 7 day week. There can be no jumps in weeks so include any work-free weeks also. 

Start by typing the week names down the `WEEK NAME` column. Then give the semester name in the `SEMESTER NAME` column beside the first week of each semester. The name should only appear beside the first week and the semester name must be unique. 

Now give the start date of the first listed week in the `START_DATE` column. Only one date should be given and it must be in the `YYYY-MM-DD` format. Check that the date is still in this format with a text editor if you are using a spreadsheet program.

Next, for each week give a value in the workload column. This value represents how much work you want to do that week relative to all the other weeks in that semester. The target hours worked for the week is found by dividing the workload by the sum of the workloads for the semester and then multiplying it by the total number of hours each of that semester's projects will take. You can give a value of zero if you are not planning on working that week.

The next four columns from `PROJECT_NAME` to `TOTAL_HOURS` form the next block of data. Each row represents a Toggl project that is being tracked. Only Toggl projects listed here will be included in the analysis.

You need to determine the project IDs of all the projects that are being tracked. The included `projects.py` script can be used for this. Run `python3 projects.py API_TOKEN` replacing `API_TOKEN` with your API token from before. Select your workspace and then make a note of the project IDs that you want to track.

Next, list the names of all the projects you want to track under `PROJECT_NAME`. The name does not have to be the same as the name Toggl uses. Beside each of these names give its project ID. Now give the semester each project is occurring in. These must be identical to the semester names given before. An `ALL` semester can be given if the project occurs over all semesters. Now, in the `TOTAL_HOURS` column give the total number of hours the project should take. It is assumed that if the project occurs over all semesters it will have its hours shared equally among each.

The last two columns make up the list of Toggl tags to be tracked. Up to 5 can be given. The `TRACKED_TAGS` column should contain the name Toggl uses for the tag and the `TAG_SYMBOL` column should contain a short name (max. 6 char.) for each to be displayed in this program.

### Run program
To run the program type `python3 targets.py` into the terminal. To explore historical data you can enter the time machine by typing `python3 targets.py -t YYYY-MM-DD HH:MM:SS` instead. If you pick a time during which a tracked timer was running, all of the then running timer's final duration will be included; not just up to the given time! Only time entries from active projects are included in the analysis, so if you have archived an old project time machine won't be able to see it.

Note: you need to make sure you have `python3` installed. The `curses` package also must be installed; is doesn't come with Python by default on Windows. Other required packages should come with Python on all platforms.

