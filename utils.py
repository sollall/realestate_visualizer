#utilsじゃなくてcommon.pyを別で作ってもいいかも
import numpy as np

def sigmoid(x, gain=1, offset_x=0):
    return ((np.tanh(((x+offset_x)*gain)/2)+1)/2)

# Function to scale colors
def scale_color(value, gain=0.01, offset=-400):
    # Normalize the value to be between 0 and 1
    normalized=sigmoid(value,gain=gain,offset_x=offset)
    # Define a 7-color scale (e.g., from blue to red)
    colors = [
        [0, 0, 255, 160],   # Blue
        [0, 128, 255, 160], # Light Blue
        [0, 255, 255, 160], # Cyan
        [255, 255, 0, 160], # Yellow
        [255, 165, 0, 160], # Orange
        [255, 69, 0, 160],  # Orange Red
        [255, 0, 0, 160]    # Red
    ]
    # Map the normalized value to the corresponding color
    index = int(normalized * (len(colors) - 1))
    return colors[index]