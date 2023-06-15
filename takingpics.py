import numpy as np
import cv2

#カメラの設定　デバイスIDは0
cap = cv2.VideoCapture(0)
count = 0

# カメラの解像度を設定
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)  # 幅の設定
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)  # 高さの設定

#繰り返しのためのwhile文
while True:
    #カメラからの画像取得
    _, frame = cap.read()
    #カメラの画像の出力
    cv2.imshow('camera', frame)

    #繰り返し分から抜けるためのif文
    key = cv2.waitKey(1)
    if key == ord('a'):                 # 写真撮影
        cv2.imwrite(f'pic{count}.png',frame)
        count += 1
    elif key == 27:   #Escで終了
        break


#メモリを解放して終了するためのコマンド
cap.release()
cv2.destroyAllWindows()