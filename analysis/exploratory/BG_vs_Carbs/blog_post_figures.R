library(rpart)			#Decision Tree Creation Library
library(rpart.plot)		#Decision Tree Figure Visualization
library(extrafont)		#Custom Fonts
library(ggplot2)		#Basic Figures and Plotting

#Load Font Data
font_import(paths="FONT FILE LOCATION")
loadfonts(device="win")

# load in data
projectPath = "LOCATION OF LEAF NODE INFORMATION CSV"
leaf_df = read.csv(paste0(projectPath, "leaf_node_information_v5.csv"))


############### Distribution Plots #######################

#Set path for tree figure location
distribution_path = "A:/single_factor_trees/percent70to180.mgdL"
#distribution_path = "A:/mixed_factor_trees/percent70to180.mgdL"

setwd(distribution_path)  
images_to_make = unique(leaf_df$image_id)

for(factor_count_id in 1:length(images_to_make)){
  d=leaf_df[which(leaf_df$image_id==images_to_make[factor_count_id]),]
  d = d[order(as.double(d$leaf_label_min),decreasing=TRUE),]
  x_min = seq(0.01,.06*nrow(d),0.06)
  x_max = seq(.06,.06*nrow(d),0.06)
  median_width = (x_max-x_min)*0.725
  median_xmin = x_min+(x_max-x_min-median_width)/2
  median_xmax = x_max-(x_max-x_min-median_width)/2
  
  #png(file = paste(images_to_make[factor_count_id],"_distribution_v4.png",sep=""),width=757,height=800,units="px",res=200)
  
  ggplot(data = d) + 
    #scale_x_continuous(name="Leaf Group",limits=c(0,0.2*nrow(d)),breaks=(x_max+x_min)/2, labels=seq(1,nrow(d),1)) + 
    scale_x_continuous(name=d$factor_label,limits=c(0.005,0.06*nrow(d)+.005),breaks=(x_max+x_min)/2, labels=d$leaf_label)+ 
    #scale_y_continuous(name="% Time in Range",limits=c(0,1)) +
    geom_rect(mapping=aes(ymin=as.double(X10perc), ymax=as.double(X90perc),xmin=x_min,xmax=x_max), color=NA,fill="#d0d0d0")+
    geom_rect(mapping=aes(ymin=as.double(X25perc), ymax=as.double(X75perc),xmin=x_min,xmax=x_max), color=NA,fill="#A3A3A3") +
    geom_rect(mapping=aes(ymin=as.double(X50perc)-median_width/2, ymax=as.double(X50perc)+median_width/2,xmin=median_xmin,xmax=median_xmax), color="white",fill="#7BB895")+
    theme_classic()+
    theme(legend.position="none")+
    #xlab("Time of Day (HH:MM)")+
    ylab("Time in Range (Percent)")+ 
    #labs(title="Average BG vs Carb Entry Distribution")+
    #scale_x_discrete(limits=c(0,0.2*nrow(d)),breaks=c("1","2"))+
    scale_y_continuous(sec.axis = sec_axis(~.*24, name = "Time in Range (hours)",breaks=seq(6,24,3)),limits=c(.25,1),breaks=round(seq(.25,1,1/8),2),labels=round(seq(25,100,100/8)))+
    #scale_y_continuous(breaks=round(seq(.25,1,1/8),2),labels=round(seq(25,100,100/8)))+
    theme(plot.title = element_text(size=20,family="Nunito",face="bold",color="#454545",hjust=0))+
    theme(axis.title = element_text(size=20*(7/8),family="Roboto Mono",face="bold",color="#a1a1a1"))+
    theme(axis.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c"))+
    theme(axis.title.y = element_text(margin = margin(t = 0, r = 15, b = 0, l = 0)))+
    theme(axis.title.x = element_text(margin = margin(t = 15, r = 0, b = 0, l = 0)))+
    theme(axis.text.x = element_text(hjust=0.45))+
    theme(axis.title.y.right = element_text(margin = margin(t = 0, r = 0, b = 0, l = 15)))+
    theme(axis.title.x.top = element_text(vjust=2.5))+
    theme(axis.text.x.top=element_text(hjust=0.6, margin = margin(t = 0, r = 0, b = 4, l = 0)))+
    #scale_x_reverse(limits=rev(c(0.005,0.06*nrow(d)+.005)))+
    coord_flip()+
    theme(aspect.ratio = (.06*nrow(d)+0.01)/.75)
    
    
    
    
    
  
  #geom_text(data=leaf_df, aes(xmin=X25perc,xmax=X75perc,ymin=1,ymax=2), size=4) 
  #print(p)
  #dev.off()
  
  #ggsave(file=paste(images_to_make[factor_count_id],"_distribution_v5.png",sep=""), device="png", path=distribution_path, width=3.32+((nrow(d)-2)*0.8), height=5,dpi=300)
  #ggsave(file=paste(images_to_make[factor_count_id],"_distribution_v4.svg",sep=""), device="svg", path=distribution_path, width=3.32+((nrow(d)-2)*0.8), height=5,dpi=300)
  ggsave(file=paste(images_to_make[factor_count_id],"_distribution_v5.png",sep=""), device="png", width = 8, height = 6, units="in",path=distribution_path, dpi=96)
  
  #Create label information
  d = d[order(as.double(d$leaf_label_min),decreasing=FALSE),]
  perc_vals = round(100*as.double(as.character(d$mean)),1)
  str_hour_vals = sprintf("%.3f",24*perc_vals/100)
  hour_min_matrix = matrix(unlist(strsplit(str_hour_vals,".",fixed=TRUE)),nrow=2)
  hours = as.integer(unlist(hour_min_matrix[1,]))
  mins = as.character(round(as.double(hour_min_matrix[2,])/1000*60))
  time_labels=paste(sprintf("%.1f",perc_vals),"%"," - ",hours,"h ", mins, "m",sep="")
  
  
  ggplot(d,aes(x=d$leaf_label,y=100*as.double(as.character(d$mean)))) + 
    geom_bar(stat = "identity",width=0.8,fill="#7BB895")+
    theme_classic() + 
    xlab(d$factor_label[1])+
    #ylab("testy")+ 
    labs(title="Average Percent Time in Range")+
    theme(legend.position="none",axis.text.x = element_text(angle = 90, hjust = 1,vjust=.5))+
    #scale_fill_manual(values=c(fill_color))+
    theme(plot.title = element_text(size=20,family="Nunito",face="bold",color="#454545",hjust=0.5))+
    theme(axis.title = element_text(size=20*(7/8),family="Roboto Mono",face="bold",color="#a1a1a1"))+
    theme(axis.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c",vjust=0.4))+
    #theme(axis.title.y = element_text(margin = margin(t = 0, r = 15, b = 0, l = 0)))+
    theme(axis.title.x = element_blank())+
    theme(axis.line.x = element_blank())+
    theme(axis.text.x=element_blank())+
    theme(axis.ticks.x = element_blank())+
    #theme(axis.title.x = element_text(margin = margin(t = 15, r = 0, b = 0, l = 0)))+
    theme(axis.title.y = element_text(margin = margin(t = 0, r = 10, b = 0, l = 0)))+
    theme(axis.text.y = element_text(margin = margin(t = 0, r = 8, b = 0, l = 0)))+
    scale_x_discrete(limits=rev(d$leaf_label))+
    #scale_y_discrete(expand=c(0,0))+
    scale_y_continuous(expand=c(0,0),limits=c(0,max(perc_vals)+max(perc_vals)*0.5))+
    theme(panel.grid = element_blank(), panel.border = element_blank())+
    geom_text(colour="#a1a1a1",hjust=-0.10,vjust=0.4,aes(family="Roboto Mono",label=time_labels))+
    coord_flip()
    #theme(aspect.ratio = .2+(nrow(d)-2)*0.2)
  
  #ggsave(file=paste(images_to_make[factor_count_id],"_barchart_v5.png",sep=""), device="png", path=distribution_path, width=3.32+((nrow(d)-2)*0.8), height=5,dpi=300)
  ggsave(file=paste(images_to_make[factor_count_id],"_barchart_v5.png",sep=""), device="png", width=8,height=6,units="in", path=distribution_path,dpi=96)
  
  #ggsave(file=paste(images_to_make[factor_count_id],"_barchart_v4.svg",sep=""), device="svg", path=distribution_path, width=3.32+((nrow(d)-2)*0.8), height=5,dpi=300)
  
}


##################### MISC FIGURES ########################
########### Create Boxplots of undivided groups ###########

### Binning data information
carb_breaks = c(0,50,250,400)
carb_labels = c("1-50","51-250","251-400")

age_breaks2 = c(0,5,8,11,14,17,20,24,29,34,39,44,49,54,59,64,85)
age_labels2 = c("1-5","6-8","9-11","12-14","15-17","18-20","21-24","25-29","30-34","35-39","40-44","45-49","50-54","55-59","60-64","65-85")

years_with_diabetes_breaks1 = c(-1,2,5,9,14,19,24,29,39,49,75)
years_with_diabetes_labels1 = c("0-2","3-5","6-9","10-14","15-19","20-24","25-29","30-39","40-49","50-75")

diagnosis_breaks1 = c(-1,2,5,9,14,19,24,29,39,49,75)
diagnosis_labels1 = c("0-2","3-5","6-9","10-14","15-19","20-24","25-29","30-39","40-49","50-75")

age_by_group = cut(data$age,breaks=age_breaks2,labels=age_labels2)
carb_by_group = cut(data$totalDailyCarbs,breaks=carb_breaks,labels=carb_labels)
diagnosed_age_group = cut(data$diagnosisAge,breaks=diagnosis_breaks1,labels=diagnosis_labels1)
years_with_diabetes_group = cut(data$yearsLivingWithDiabetes,breaks=years_with_diabetes_breaks1,labels=years_with_diabetes_labels1)

data$carb_group = carb_by_group
data$age_group = age_by_group
data$diagnosed_age_group = diagnosed_age_group
data$years_with_diabetes_group = years_with_diabetes_group 

ggplot() + 
  geom_boxplot(aes(x=data$age_group,y=data$percent70to180.mgdL)) + 
  theme_classic() + 
  xlab("Age")+
  ylab("Daily 70-180 % TIR")+ 
  labs(title="Age vs %TIR 70-180")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1))
