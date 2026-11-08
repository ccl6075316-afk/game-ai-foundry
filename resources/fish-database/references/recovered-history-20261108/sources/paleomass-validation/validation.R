
library(paleomass)

# Set the working directory to the folder from unzipping the zip 
# file that contained this script file.

###
### Sphere
###

flist <- list.files("Sphere",pattern=".png")
rlist <- sort(as.numeric(substr(flist,1,nchar(flist)-4)))
accuracy <- NULL
for(i in 1:length(rlist)){
  tfile <- paste0(rlist[i])
  try(paleomass(Folder="Sphere",BodyL.File=tfile,BodyV.File=tfile,
                Save.Total.Mesh=F,Save.Part.Mesh = F))
  rslt <- read.csv("./Sphere/Results_Sphere_interpolated.csv",row.names=1)
  
  accuracy <- rbind(accuracy,c(rlist[i],rslt[1,1]/(4/3*pi*(rlist[i]/2)^3),
                               rslt[1,2]/(4 * pi *(rlist[i]/2)^2)))
}
colnames(accuracy) <- c("Axial_length","Est_vs_true_Volulme","Est_vs_true_SA")
write.csv(accuracy,file="Sphere_validation.csv")


#accuracy <- read.csv(file="Sphere_validation.csv",row.names=1)

sc <- c(100,1000,10000)
sc2 <- c(seq(100,900,100),seq(1000,10000,1000))
ysc <- seq(0.95,1.01,0.01)
ysc2 <- c("-5%","-4%","-3%","-2%","-1%","0%","1%")

plot(log10(accuracy[,1]),accuracy[,2],type="n",axes=F,ylim=c(0.95,1.01),
     xlab="Resolution (dots per body axis length)",ylab="Error")
rect(1,0.995,5,1.005,col=scales::alpha(2,0.5),border=F)
lines(log10(accuracy[,1]),accuracy[,2],lwd=2)
lines(log10(accuracy[,1]),accuracy[,3],col=4,lwd=2)
axis(2,at=ysc,labels=ysc2,las=1)
axis(1,at=log10(sc),labels=sc)
axis(1,at=log10(sc2),labels=F)
abline(h=1,col=2)
box()

plot(accuracy[,1],accuracy[,2],type="n",axes=T,ylim=c(0.95,1.01))
rect(0,0.995,10000,1.005,col=scales::alpha(2,0.5),border=F)
lines(accuracy[,1],accuracy[,2],lwd=2)
lines(accuracy[,1],accuracy[,3],col=4,lwd=2)
abline(h=1,col=2)


###
### Prolate Ellipsoid
###

flist <- list.files("Ellipsoid",pattern=".png")
rlist <- sort(as.numeric(substr(flist,1,nchar(flist)-4)))
accuracy.ellipsoid <- NULL
for(i in 1:length(rlist)){
  tfile <- paste0(rlist[i])
  try(paleomass(Folder="Ellipsoid",BodyL.File=tfile,BodyV.File=tfile,
                Save.Total.Mesh=F,Save.Part.Mesh = T))
  rslt <- read.csv("./Ellipsoid/Results_Ellipsoid_interpolated.csv",row.names=1)
  c <- rlist[i]/2; a <- 0.2*c
  ee <- (1-(a/c)^2)^0.5
  sa <- 2*pi*(a^2)*(1+(5/ee)*asin(ee))
  v <- 4/3 * pi * c * a^2
  accuracy.ellipsoid <- rbind(accuracy.ellipsoid,c(rlist[i],rslt[1,1]/v,
                                                   rslt[1,2]/sa))
}
colnames(accuracy.ellipsoid) <- c("Axial_length","Est_vs_true_Volulme","Est_vs_true_SA")
write.csv(accuracy.ellipsoid,file="Ellipsoid_validation.csv")


#accuracy.ellipsoid <- read.csv(file="Ellipsoid_validation.csv",row.names=1)

sc <- c(100,1000,10000)
sc2 <- c(seq(100,900,100),seq(1000,10000,1000))
ysc <- seq(0.95,1.01,0.01)
ysc2 <- c("-5%","-4%","-3%","-2%","-1%","0%","1%")

plot(log10(accuracy.ellipsoid[,1]),accuracy.ellipsoid[,2],type="n",axes=F,
     xlab="Resolution (dots per body axis length)",ylab="Error",ylim=c(0.95,1.01))
rect(1,0.995,5,1.005,col=scales::alpha(2,0.5),border=F)
lines(log10(accuracy.ellipsoid[,1]),accuracy.ellipsoid[,2],lwd=2)
lines(log10(accuracy.ellipsoid[,1]),accuracy.ellipsoid[,3],col=4,lwd=2)
axis(2,at=ysc,labels=ysc2,las=1)
axis(1,at=log10(sc),labels=sc)
axis(1,at=log10(sc2),labels=F)
abline(h=1,col=2)
box()

plot(accuracy.ellipsoid[,1],accuracy.ellipsoid[,2],type="n",axes=T,ylim=c(0.95,1.01))
rect(0,0.995,10000,1.005,col=scales::alpha(2,0.5),border=F)
lines(accuracy.ellipsoid[,1],accuracy.ellipsoid[,2],lwd=2)
lines(accuracy.ellipsoid[,1],accuracy.ellipsoid[,3],col=4,lwd=2)
abline(h=1,col=2)


x11(h=4.5,w=7.7)
#pdf(h=4.5,w=7.7,file="Geometry_Error.pdf")
layout(matrix(seq(1,2),1,2))
plot(log10(accuracy[,1]),accuracy[,2],type="n",axes=F,ylim=c(0.95,1.01),
     xlab="Resolution (dots per body axis length)",ylab="Error")
rect(1,0.995,5,1.005,col=scales::alpha(2,0.5),border=F)
lines(log10(accuracy[,1]),accuracy[,2],lwd=2)
lines(log10(accuracy[,1]),accuracy[,3],col=4,lwd=2)
axis(2,at=ysc,labels=ysc2,las=1)
axis(1,at=log10(sc),labels=sc)
axis(1,at=log10(sc2),labels=F)
abline(h=1,col=2)
box()
plot(log10(accuracy.ellipsoid[,1]),accuracy.ellipsoid[,2],type="n",axes=F,
     xlab="Resolution (dots per body axis length)",ylab="Error",ylim=c(0.95,1.01))
rect(1,0.995,5,1.005,col=scales::alpha(2,0.5),border=F)
lines(log10(accuracy.ellipsoid[,1]),accuracy.ellipsoid[,2],lwd=2)
lines(log10(accuracy.ellipsoid[,1]),accuracy.ellipsoid[,3],col=4,lwd=2)
axis(2,at=ysc,labels=ysc2,las=1)
axis(1,at=log10(sc),labels=sc)
axis(1,at=log10(sc2),labels=F)
abline(h=1,col=2)
box()
#dev.off()  


###
### Vertebrates
###

BALs <- na.omit(read.csv("BALengths.csv"))
sps <- BALs[,1]
ns <- seq(1.5,3.0,0.2)
SAs <- Volumes <- NULL
for(i in 1:length(sps)){
  sas <- volumes <- NULL
  fldr <- sps[i]
  print(fldr)
  for(j in 1:length(ns)){
    N1 <- ns[j]
    N2 <- N1 + 0.1
    tmpR <- paleomass(Folder=fldr,n1=N1,n2=N2,nn.f=0.1,cfin.thick=BALs[i,3],
                      dfin.thick=BALs[i,3],ffin.thick=BALs[i,3],hfin.thick=BALs[i,3],
                      afin.thick=BALs[i,4],d2fin.thick=BALs[i,4],body.axis.l=BALs[i,2],
                      Plot.Result.Mesh = F, Save.Total.Mesh = F)
    volumes <- c(volumes, tmpR[12:13,3])
    sas <- c(sas, tmpR[12:13,4])
  }
  Volumes <- cbind(Volumes,volumes)
  SAs <- cbind(SAs,sas)
}
colnames(SAs) <- colnames(Volumes) <- sps
write.csv(t(Volumes),file="Validate_V.csv")
write.csv(t(SAs),file="Validate_SA.csv")



###
### Examples for assembled model
###

### Takifugu_snyderi
paleomass(Folder="Takifugu_snyderi",n1=2,n2=3,nn.f=0.1,cfin.thick=5,dfin.thick=3,
          ffin.thick=3,hfin.thick=3,afin.thick=3,body.axis.l=0.1274179,
          cfin.onset=0.95,cfin.adj.up=80,
          ffin.onset=0.294,ffin.adj.up=500,ffin.adj.lat=-450,
          ffin.pitch=0,ffin.yaw=pi/2,
          dfin.onset=0.613,
          afin.onset=0.639,afin.adj.up=50,afin.pitch=pi*11/180)

### Tursiops truncatus

N1 <- 1.5; N2 <- 3
N1 <- 2; N2 <- 2.5
paleomass(Folder="Tursiops_truncatus",n1=N1,n2=N2,nn.f=0.1,cfin.thick=20,dfin.thick=20,
         ffin.thick=20,hfin.thick=20,afin.thick=20,body.axis.l=2.369443,
         cfin.roll=pi/2,cfin.adj.up=0,cfin.adj.lat=0,cfin.pitch=pi/20,cfin.onset=0.934,
         ffin.pitch=0,ffin.adj.up=250,ffin.adj.lat=-200,ffin.onset=0.258,ffin.roll=pi*70/180,
         dfin.pitch=0,dfin.adj.up=0,dfin.onset=0.453)


### Sphyrna_lewini
paleomass(Folder="Sphyrna_lewini",n1=1.8,n2=2,nn.f=0.1,body.axis.l=0.565,
          cfin.thick=20,dfin.thick=20,ffin.thick=20,hfin.thick=20,afin.thick=20,
          cfin.onset=0.78,cfin.adj.up=200,cfin.adj.lat=0,cfin.pitch=-pi/4,
          ffin.onset=0.232,ffin.adj.up=80,ffin.adj.lat=-120,
          hfin.onset=0.494,hfin.adj.up=150,hfin.adj.lat=-100,
          dfin.onset=0.274,dfin.adj.up=0,
          d2fin.onset=0.626,d2fin.adj.up=75,
          afin.onset=0.603,afin.adj.up=110,
          ceph.roll=pi/2,ceph.adj.up=150)

### Lateolabrax_japonicus
N1 <- 2; N2 <- 2.5
paleomass(Folder="Lateolabrax_japonicus",n1=N1,n2=N2,nn.f=0.1,cfin.thick=20,dfin.thick=5,
          ffin.thick=5,hfin.thick=5,afin.thick=5,body.axis.l=0.4329004,
          cfin.roll=0,cfin.adj.up=155,cfin.yaw=0,cfin.onset=0.87,
          ffin.pitch=-pi/10,ffin.roll=2*pi/5,ffin.adj.up=400,ffin.adj.lat=-70,ffin.onset=0.287,
          dfin.pitch=55*pi/180,dfin.adj.up=220,dfin.onset=0.470,
          hfin.pitch=0,hfin.onset=0.322,hfin.adj.up=120,hfin.adj.lat=-170,
          afin.onset=0.563,afin.adj.up=0,
          d2fin.pitch=30*pi/180,d2fin.onset=0.563,d2fin.adj.up=0)

### Eopsetta_grigorjewi
paleomass(Folder="Eopsetta_grigorjewi",n1=1.6,n2=1.7,nn.f=0.1,cfin.thick=20,dfin.thick=5,
          ffin.thick=5,hfin.thick=5,afin.thick=5,body.axis.l=0.2751836,
          cfin.roll=0,cfin.adj.up=455,cfin.yaw=0,cfin.onset=0.9,
          ffin.pitch=-pi/10,ffin.roll=2*pi/5,ffin.adj.up=500,ffin.adj.lat=-15,ffin.onset=0.2,
          dfin.pitch=82*pi/180,dfin.adj.up=2200,dfin.onset=0.9,
          hfin.pitch=0,hfin.onset=0.2,hfin.adj.up=50,hfin.adj.lat=-120,
          afin.onset=0.25,afin.adj.up=110,afin.pitch=-pi*76/180,
          d2fin.pitch=-35*pi/180,d2fin.onset=0.55,d2fin.adj.up=180)

### Scomber_japonicus
paleomass(Folder="Scomber_japonicus",n1=2,n2=3,nn.f=0.1,cfin.thick=20,dfin.thick=5,
          ffin.thick=5,hfin.thick=5,afin.thick=5,body.axis.l=0.2797172,
          cfin.roll=0,cfin.adj.up=0,cfin.yaw=0,cfin.onset=900,
          ffin.pitch=-pi/10,ffin.roll=2*pi/5,ffin.adj.up=-12,ffin.adj.lat=-15,ffin.onset=257,
          dfin.pitch=0,dfin.adj.up=150,dfin.onset=333,
          hfin.pitch=0,hfin.onset=304,hfin.adj.up=-50,hfin.adj.lat=-70,
          afin.onset=635,afin.adj.up=25,
          d2fin.pitch=-35*pi/180,d2fin.onset=624,d2fin.adj.up=180)

### Anguilla_marmorata
paleomass(Folder="Anguilla_marmorata",n1=2.5,n2=3,nn.f=0.1,dfin.thick=5,
          ffin.thick=5,afin.thick=5,body.axis.l=0.758526,
          ffin.pitch=pi*0/180,ffin.roll=pi*50/180,ffin.adj.up=130,ffin.adj.lat=-30,ffin.onset=0.122,
          dfin.pitch=pi*51/180,dfin.adj.up=620,dfin.onset=0.719,
          afin.onset=0.4335,afin.adj.up=115,afin.pitch = -53.85*pi/180,
          )


