#utilsじゃなくてcommon.pyを別で作ってもいいかも
import numpy as np

def sigmoid(x, gain=1, offset_x=0):
    return ((np.tanh(((x+offset_x)*gain)/2)+1)/2)
