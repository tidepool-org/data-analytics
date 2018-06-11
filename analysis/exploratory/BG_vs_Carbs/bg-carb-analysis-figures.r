############################## START FIGURE OUTPUT ################################

#Set your figure output location
output_location = "YOUR_OUTPUT_FILE_LOCATION"

plot_histogram <- function(data_source, feature, fill_color, bin_width, xlimits, break_sequence, title_text,ylab_text,xlab_text,filename) {
  
  ggplot(data=data_source) + 
    geom_histogram(aes(feature),binwidth=bin_width,fill=fill_color,color="white")+
    theme_classic()+
    theme(legend.position="none")+
    xlab(xlab_text)+
    ylab(ylab_text)+ 
    labs(title=title_text)+
    scale_x_continuous(limits=xlimits,breaks=break_sequence)+
    theme(plot.title = element_text(size=20,family="Nunito",face="bold",color="#454545",hjust=0.5))+
    theme(axis.title = element_text(size=20*(7/8),family="Roboto Mono",face="bold",color="#a1a1a1"))+
    theme(axis.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c"))+
    theme(axis.title.y = element_text(margin = margin(t = 0, r = 15, b = 0, l = 0)))+
    theme(axis.title.x = element_text(margin = margin(t = 15, r = 0, b = 0, l = 0)))
    #stat_count(geom="text", aes(x=feature,label=..count..), binwidth=bin_width,vjust=-1)
  
  #ggsave(file=filename, path=output_location, width=6.4, height=4.8, dpi=300, units="in")
}

plot_histogram(df,medianBG,"grey", 5,c(0,400),seq(0,400,50),"Daily Median Blood Glucose Histogram","Day Count", "Median Blood Glucose (mg/dL)","median_hist.png")
plot_histogram(df,meanBG,"grey", 5,c(0,400),seq(0,400,50),"Daily Mean Blood Glucose Histogram","Day Count", "Mean Blood Glucose (mg/dL)","mean_hist.png")
plot_histogram(df,stddevBG,"grey", 4,c(0,140),seq(0,140,10),"Daily Blood Glucose Standard Deviation Histogram","Day Count", "Blood Glucose Standard Deviation (mg/dL)","stddev_hist.png")
plot_histogram(df,daily_CV,"grey", 2,c(0,80),seq(0,80,10),"Daily Blood Glucose Coefficient of Variation Histogram","Day Count", "Blood Glucose Coefficient of Variation","cv_hist.png")
plot_histogram(df,daily_range,"grey", 5,c(0,400),seq(0,400,50),"Daily Blood Glucose Range Histogram","Day Count", "Blood Glucose Range (mg/dL)","range_hist.png")
plot_histogram(df,daily_25_75_IQR,"grey", 4,c(0,140),seq(0,140,10),"Daily Blood Glucose 25-75 IQR Histogram","Day Count", "Blood Glucose 25-75 IQR (mg/dL)","25_75_IQR_hist.png")

plot_histogram(df,daily_cgm_events,"grey", 2,NULL,c(seq(min(df$daily_cgm_events),max(df$daily_cgm_events),10),max(df$daily_cgm_events)),"Daily CGM Events Histogram","Day Count", "Number of CGM Events Observed","cgm_event_hist.png")
plot_histogram(df,daily_carb_events,"grey", 1,NULL,c(seq(min(df$daily_carb_events),max(df$daily_carb_events),1),max(df$daily_carb_events)),"Daily Carb Events Histogram","Day Count", "Number of Carb Events Observed","carb_event_hist.png")


######### Time in Range Plots ##############

group_names = levels(big.df$carb_group)
age_ranges = levels(big.df$age_group)
df_TIR = c()

range_names = c("Above 250", "Above 180", "Between 70-180","Below 70","Below 54")
range_colors = c("#A18BC9","#CAAEFC","#7BB895","#FC9888","#D68174")

############### TIME IN RANGE SUMMARIES #############

for(carb_group in 1:length(group_names)){
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>250))/length(which(big.df$carb_group==group_names[carb_group])), range_names[1]))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>180))/length(which(big.df$carb_group==group_names[carb_group])), range_names[2]))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]>=70 & big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<=180))/length(which(big.df$carb_group==group_names[carb_group])), range_names[3]))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<70))/length(which(big.df$carb_group==group_names[carb_group])), range_names[4]))
  df_TIR = rbind(df_TIR, c(group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$carb_group==group_names[carb_group])]<54))/length(which(big.df$carb_group==group_names[carb_group])), range_names[5]))
}

df_TIR = data.frame(df_TIR)
colnames(df_TIR)=c("carb_group","time_in_range","range_name")
df_TIR$carb_group = factor(df_TIR$carb_group,levels=unique(df_TIR$carb_group))
df_TIR$range_name = factor(df_TIR$range_name,levels=unique(df_TIR$range_name))

## Plot All Glucose Range + Carb Ranges together
ggplot(df_TIR, aes(fill=as.factor(range_name), y=as.double(as.character(time_in_range)), x=as.factor(carb_group))) + 
  geom_bar( stat="identity",position="dodge")+
  theme_classic() + 
  xlab("Total Daily Carb Intake (g)")+
  ylab("% Time in Range")+ 
  labs(title="Daily Carb Intake vs % Time in Range")+
  theme(axis.text.x = element_text(angle = 90, hjust = 1,vjust=.5))+
  scale_fill_manual(values=range_colors)+
  labs(fill='Blood Glucose \nRange (mg/dL)')+
  theme(plot.title = element_text(size=20,family="Nunito",face="bold",color="#454545",hjust=0.5))+
  theme(axis.title = element_text(size=20*(7/8),family="Roboto Mono",face="bold",color="#a1a1a1"))+
  theme(axis.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c"))+
  theme(axis.title.y = element_text(margin = margin(t = 0, r = 15, b = 0, l = 0)))+
  theme(axis.title.x = element_text(margin = margin(t = 15, r = 0, b = 0, l = 0)))+
  theme(legend.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#a1a1a1"))+
  theme(legend.title = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c"))+
  scale_x_discrete(limits=rev(levels(df_TIR$carb_group)))+
  coord_flip()
#geom_text(aes(label=as.integer(as.character(time_in_range))), position=position_dodge(width=0.9), vjust=-0.25)

#ggsave(file="test.png", path=output_location, width=12, height=8, dpi=300, units="in")


plot_TIR_bar <- function(bg_range, fill_color,xlab_text,ylab_text,title_text,filename){
  
  #Create label information
  perc_vals = round(as.double(as.character(subset(df_TIR, range_name %in% c(bg_range))$time_in_range)),1)
  str_hour_vals = sprintf("%.3f",24*perc_vals/100)
  hour_min_matrix = matrix(unlist(strsplit(str_hour_vals,".",fixed=TRUE)),nrow=2)
  hours = as.integer(unlist(hour_min_matrix[1,]))
  mins = as.character(round(as.double(hour_min_matrix[2,])/1000*60))
  time_labels=paste(sprintf("%.1f",perc_vals),"%"," - ",hours,"h ", mins, "m",sep="")
  
  ggplot(subset(df_TIR, range_name %in% c(bg_range)),aes(x=as.factor(carb_group),y=as.double(as.character(time_in_range)))) + 
    geom_bar(stat = "identity",aes(fill=fill_color),width=0.8)+
    theme_classic() + 
    xlab(xlab_text)+
    ylab(ylab_text)+ 
    labs(title=title_text)+
    theme(legend.position="none",axis.text.x = element_text(angle = 90, hjust = 1,vjust=.5))+
    scale_fill_manual(values=c(fill_color))+
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
    scale_x_discrete(limits=rev(levels(df_TIR$carb_group)))+
    #scale_y_discrete(expand=c(0,0))+
    scale_y_continuous(expand=c(0,0),limits=c(0,max(perc_vals)+max(perc_vals)*0.5))+
    theme(panel.grid = element_blank(), panel.border = element_blank())+
    geom_text(colour="#a1a1a1",hjust=-0.10,vjust=0.4,aes(family="Roboto Mono",label=time_labels))+
    coord_flip()
  #ggsave(file=filename, path=output_location, dpi=300, units="in")
  ggsave(file=filename, path=output_location, width=6.4, height=4.8, dpi=300, units="in")
}

#Output %TIR figures for each range
for(k in 1:length(range_names)){
  plot_TIR_bar(range_names[k],range_colors[k],"Daily Carb Intake (g)","% Time in Range",paste("Percent Time ",range_names[k]," mg/dL",sep=""),paste("ALL_PERC_",range_names[k],".png",sep=""))
}

#################### AGE SPECIFIC TIME IN RANGES #########################

#### Currently have a problem here where there is not enough data to fill every required data interaction


df_TIR=c()


for(carb_group in 1:length(group_names)){
  for(age_group_val in 1:length(age_ranges)){
  df_TIR = rbind(df_TIR, c(age_ranges[age_group_val],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]>250))/length(which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])), range_names[1],length(unique(big.df$big.day[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])])),length(unique(big.df$big.filename[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]))))
  df_TIR = rbind(df_TIR, c(age_ranges[age_group_val],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]>180))/length(which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])), range_names[2],length(unique(big.df$big.day[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])])),length(unique(big.df$big.filename[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]))))
  df_TIR = rbind(df_TIR, c(age_ranges[age_group_val],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]>=70 & big.df$big.bg[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]<=180))/length(which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])), range_names[3],length(unique(big.df$big.day[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])])),length(unique(big.df$big.filename[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]))))
  df_TIR = rbind(df_TIR, c(age_ranges[age_group_val],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]<70))/length(which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])), range_names[4],length(unique(big.df$big.day[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])])),length(unique(big.df$big.filename[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]))))
  df_TIR = rbind(df_TIR, c(age_ranges[age_group_val],group_names[carb_group], 100*length(which(big.df$big.bg[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]<54))/length(which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])), range_names[5],length(unique(big.df$big.day[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])])),length(unique(big.df$big.filename[which(big.df$age_group[which(big.df$carb_group==group_names[carb_group])]==age_ranges[age_group_val])]))))
  
  cat(paste(carb_group,"/21 * ", age_group_val,"/14\n",sep=""))
  }
}

df_TIR = data.frame(df_TIR)
colnames(df_TIR)=c("age_group","carb_group","time_in_range","range_name","unique_days","unique_donors")
df_TIR$age_group = factor(df_TIR$age_group,levels=unique(df_TIR$age_group))
df_TIR$carb_group = factor(df_TIR$carb_group,levels=unique(df_TIR$carb_group))
df_TIR$range_name = factor(df_TIR$range_name,levels=unique(df_TIR$range_name))


########################## PLOT CARBS VS TIME ###########################