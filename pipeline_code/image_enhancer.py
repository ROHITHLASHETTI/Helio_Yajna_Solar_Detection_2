import cv2
import numpy as np

def enhance_image(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    enhanced = cv2.cvtColor(cv2.merge((l,a,b)), cv2.COLOR_LAB2BGR)
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    enhanced = cv2.filter2D(enhanced, -1, kernel)
    return enhanced