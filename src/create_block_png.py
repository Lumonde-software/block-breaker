import cv2
import numpy as np
import block_breaker as bb

# img = np.full((bb.BLOCK_SIZE, bb.BLOCK_SIZE, 3), 0, dtype=np.uint8)
# for B in range(256):
#     for G in range(256):
#         for R in range(256):
#             cv2.rectangle(img, (1, 1), (bb.BLOCK_SIZE-2, bb.BLOCK_SIZE-2), (B, G, R), thickness=-1)
#             cv2.imwrite('blocks/'+str(B)+'_'+str(G)+'_'+str(R)+'.png', img)