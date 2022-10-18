import cv2

def sample():
    face_cascade_path = '/home/denjo/experiment/cvgl/opencv/data/haarcascades/haarcascade_frontalface_default.xml'

    face_cascade = cv2.CascadeClassifier(face_cascade_path)

    src = cv2.imread('data/man.webp')
    src_gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)

    faces = face_cascade.detectMultiScale(src_gray)

    for x, y, w, h in faces:
        cv2.rectangle(src, (x, y), (x + w, y + h), (255, 0, 0), 2)
        
    cv2.imwrite('processed/man_after.png', src)