from psychopy import visual, core, event, gui
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
import random
import pandas as pd

# --- Participant Info ---
# Prompt the participant to enter their ID/name
exp_info = {"Participant ID": ""}
dlg = gui.DlgFromDict(dictionary=exp_info, title="Experiment Info")
if not dlg.OK:
    core.quit()  # User pressed cancel
participant_id = exp_info["Participant ID"]

# --- Setup ---
# Create a PsychoPy window
win = visual.Window(fullscr=True, units="height")

# Display a welcome message and wait for a key press to start the experiment
welcome_text = visual.TextStim(
    win,
    text="Welcome to our sensory-motor experiment .\n\n You will be prompted with a stimulus and expected to\n\n imagine arm movements with respect to the stimulus.\n\n Press any key to begin.",
    color="white",
    height=0.05,
)
welcome_text.draw()
win.flip()
event.waitKeys()  # Wait for the participant to press any key

# Create an experiment clock to record stimulus onset times
exp_clock = core.Clock()

# Define your stimuli list
stimuli = ["left", "right", "L", "R", "←", "→"]

# Define a marker mapping for each stimulus (customize as needed)
marker_mapping = {"left": 1, "right": 2, "L": 3, "R": 4, "←": 5, "→": 6}

# Initialize an event log list to store stimulus events
# Each event will be stored as a dictionary with participant id, stimulus label, marker, and onset time
event_log = []

# Set up BrainFlow parameters for the Cyton board
params = BrainFlowInputParams()
board_id = BoardIds.SYNTHETIC_BOARD.value  # Board ID for the Cyton board (0 if no Daisy, 2 if Daisy, BoardIds.SYNTHETIC_BOARD.value for synthetic)
board = BoardShim(board_id, params)
BoardShim.enable_dev_board_logger()
board.prepare_session()
board.start_stream()  # Start collecting EEG data

try:
    # Main experiment loop: run indefinitely until 'escape' is pressed
    while True:
        # Randomize the order of stimuli for each block
        random.shuffle(stimuli)
        for stim in stimuli:
            # --- Rest period ---
            rest_message = visual.TextStim(win, text="Rest", color="white", height=0.15)
            rest_message.draw()
            win.flip()
            core.wait(1.5)  # Rest duration

            # --- Ready period ---
            ready_message = visual.TextStim(win, text="Ready", color="white", height=0.15)
            ready_message.draw()
            win.flip()
            core.wait(1)  # Ready duration

            # --- Stimulus presentation ---
            # Record the onset time for the stimulus
            onset_time = exp_clock.getTime()

            # Create and display the stimulus
            stim_text = visual.TextStim(win, text=stim, color="white", height=0.15)
            stim_text.draw()
            win.flip()

            # Get the marker for the current stimulus and send it to the EEG stream
            marker_value = marker_mapping.get(stim, 0)
            board.insert_marker(marker_value)

            # Log the stimulus event along with participant id and timestamp
            event_log.append(
                {
                    "participant_id": participant_id,
                    "stimulus": stim,
                    "marker": marker_value,
                    "time": onset_time,
                }
            )

            # Keep the stimulus on-screen for 1 second
            core.wait(2.0)

            # Check for 'escape' key to exit the experiment
            if "escape" in event.getKeys():
                raise KeyboardInterrupt

except KeyboardInterrupt:
    print("Experiment terminated by user.")

finally:
    # --- EEG Data Saving ---
    # Stop the EEG data stream
    board.stop_stream()

    # Retrieve EEG data from the board.
    # board.get_board_data() returns a 2D array where each row is a channel and columns are samples.
    eeg_data = board.get_board_data()

    # Release the BrainFlow session
    board.release_session()

    # Save EEG data to a CSV file using pandas.
    # Transpose the data so that each row represents a sample and each column represents a channel.
    df_eeg = pd.DataFrame(eeg_data.T)
    df_eeg[30] = df_eeg[30] - df_eeg[30].iloc[0]

    channel_descriptions = board.get_board_descr(board_id)
    num_rows = channel_descriptions["num_rows"]
    eeg_names = channel_descriptions["eeg_names"].split(",")
    col_names = []
    # rename df_eeg columns
    for i in range(num_rows):
        if i in channel_descriptions["eeg_channels"]:
            idx = channel_descriptions["eeg_channels"].index(i)
            col_names.append(f"{eeg_names[idx - 1]}")
        elif i in channel_descriptions["accel_channels"]:
            idx = channel_descriptions["accel_channels"].index(i)
            col_names.append(f"accel_{idx}")
        elif i in channel_descriptions["gyro_channels"]:
            idx = channel_descriptions["gyro_channels"].index(i)
            col_names.append(f"gyro_{idx}")
        elif i == channel_descriptions["timestamp_channel"]:
            col_names.append("Timestamp")
        elif i == channel_descriptions["marker_channel"]:
            col_names.append("Marker")
        else:
            col_names.append(f"ch_{i}")
    df_eeg.columns = col_names
    df_eeg.to_csv(f"data/eeg_data_{participant_id}.csv", index=False)
    print("EEG data saved to eeg_data.csv")

    # --- Event Log Saving ---
    # Convert the event log list into a DataFrame and save it as a CSV file.
    df_events = pd.DataFrame(event_log)
    df_events.to_csv(f"data/events_data_{participant_id}.csv", index=False)
    print("Event log saved to events_data.csv")

    print(f"board description: {board.get_board_descr(board_id)}\n")
    # Close the window and quit PsychoPy
    win.close()
    core.quit()
