import re
from datetime import datetime
from collections import defaultdict

# Log file path
log_file_path = 'logfile.log'

# Regular expressions to match the log lines
indicator_start_re = re.compile(r'(?P<timestamp>\S+ \S+) - INFO - Starting indicator (?P<indicator>\S+) on (?P<ticker>\S+)')
backtest_start_re = re.compile(r'(?P<timestamp>\S+ \S+) - INFO - Running backtest (?P<indicator>\S+) on (?P<ticker>\S+)')
backtest_finish_re = re.compile(r'(?P<timestamp>\S+ \S+) - INFO - Finished backtest (?P<indicator>\S+) on (?P<ticker>\S+)')

# Function to parse datetime
def parse_timestamp(timestamp):
    return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S,%f')

# Dictionaries to store start and end times
start_times = defaultdict(dict)
backtest_start_times = defaultdict(dict)
backtest_finish_times = defaultdict(dict)

# Read the log file
with open(log_file_path, 'r') as file:
    for line in file:
        indicator_start_match = indicator_start_re.match(line)
        backtest_start_match = backtest_start_re.match(line)
        backtest_finish_match = backtest_finish_re.match(line)

        if indicator_start_match:
            timestamp = parse_timestamp(indicator_start_match.group('timestamp'))
            indicator = indicator_start_match.group('indicator')
            ticker = indicator_start_match.group('ticker')
            start_times[ticker][indicator] = timestamp

        elif backtest_start_match:
            timestamp = parse_timestamp(backtest_start_match.group('timestamp'))
            indicator = backtest_start_match.group('indicator')
            ticker = backtest_start_match.group('ticker')
            backtest_start_times[ticker][indicator] = timestamp

        elif backtest_finish_match:
            timestamp = parse_timestamp(backtest_finish_match.group('timestamp'))
            indicator = backtest_finish_match.group('indicator')
            ticker = backtest_finish_match.group('ticker')
            backtest_finish_times[ticker][indicator] = timestamp

# Calculate durations
start_to_backtest_durations = defaultdict(list)
backtest_durations = defaultdict(list)

for ticker in start_times:
    for indicator in start_times[ticker]:
        if ticker in backtest_start_times and indicator in backtest_start_times[ticker]:
            start_to_backtest_duration = (backtest_start_times[ticker][indicator] - start_times[ticker][indicator]).total_seconds()
            start_to_backtest_durations[indicator].append(start_to_backtest_duration)
            start_to_backtest_durations['total'].append(start_to_backtest_duration)

        if ticker in backtest_finish_times and indicator in backtest_finish_times[ticker]:
            backtest_duration = (backtest_finish_times[ticker][indicator] - backtest_start_times[ticker][indicator]).total_seconds()
            backtest_durations[indicator].append(backtest_duration)
            backtest_durations['total'].append(backtest_duration)
# Calculate averages and print results
for indicator in start_to_backtest_durations:
    if indicator != 'total':
        avg_start_to_backtest = sum(start_to_backtest_durations[indicator]) / len(start_to_backtest_durations[indicator]) if start_to_backtest_durations[indicator] else 0
        avg_backtest = sum(backtest_durations[indicator]) / len(backtest_durations[indicator]) if backtest_durations[indicator] else 0
        print(f"Indicator {indicator}:")
        print(f"  Average time from starting indicator to running backtest: {avg_start_to_backtest:.2f} seconds")
        print(f"  Average time to complete backtest: {avg_backtest:.2f} seconds")

average_start_to_backtest = sum(start_to_backtest_durations['total']) / len(start_to_backtest_durations['total']) if start_to_backtest_durations['total'] else 0
average_backtest = sum(backtest_durations['total']) / len(backtest_durations['total']) if backtest_durations['total'] else 0

print(f"Average time from starting indicator to running backtest: {average_start_to_backtest:.2f} seconds")
print(f"Average time to complete backtest: {average_backtest:.2f} seconds")