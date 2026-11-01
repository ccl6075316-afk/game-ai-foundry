"""Native source mask from explicit part annotation; RGB is never synthesized."""
import cv2,numpy as np
def source_mask(rgba,annotation):
 cv2.setRNGSeed(141)
 h,w=rgba.shape[:2];m=np.zeros((h,w),np.uint8);cv2.fillPoly(m,[np.rint(annotation['polygon_px']).astype(np.int32)],1)
 m &= (rgba[:,:,3]>32).astype('uint8')
 if annotation.get('segmentation')=='constrained_grabcut':
  radius=int(annotation.get('search_radius_px',10));k=np.ones((radius*2+1,)*2,np.uint8);possible=cv2.dilate(m,k)>0;inner=cv2.erode(m,np.ones((11,11),np.uint8))>0
  labels=np.where(possible,cv2.GC_PR_BGD,cv2.GC_BGD).astype('uint8');labels[m>0]=cv2.GC_PR_FGD;labels[inner]=cv2.GC_FGD;labels[rgba[:,:,3]<=32]=cv2.GC_BGD
  # Source-visible root boundary stays a frozen anatomical annotation.
  if annotation.get('root_clip_polygon_px'):
   clip=np.zeros((h,w),np.uint8);cv2.fillPoly(clip,[np.rint(annotation['root_clip_polygon_px']).astype(np.int32)],1);labels[clip==0]=cv2.GC_BGD
  fg=np.zeros((1,65),np.float64);bg=np.zeros_like(fg);cv2.grabCut(cv2.cvtColor(rgba[:,:,:3],cv2.COLOR_RGB2BGR),labels,None,bg,fg,8,cv2.GC_INIT_WITH_MASK)
  m=np.isin(labels,[cv2.GC_FGD,cv2.GC_PR_FGD]).astype('uint8')
  n,lab,stats,_=cv2.connectedComponentsWithStats(m,8)
  if n>1:m=(lab==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))).astype('uint8')
  # Fill tiny interior segmentation pinholes; original source alpha still wins.
  contours,_=cv2.findContours(m,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);m[:]=0;cv2.drawContours(m,contours,-1,1,-1);m&=(rgba[:,:,3]>32).astype('uint8')
 n,lab,stats,_=cv2.connectedComponentsWithStats(m,8)
 if n>1:m=(lab==(1+np.argmax(stats[1:,cv2.CC_STAT_AREA]))).astype('uint8')
 return m.astype(bool)
