library(rpart)			#Decision Tree Creation Library
library(rpart.plot)		#Decision Tree Figure Visualization
library(extrafont)		#Custom Fonts
library(ggplot2)		#Basic Figures and Plotting

#Load Font Data
font_import(paths="FONT FILE LOCATION")
loadfonts(device="win")

# load in data
projectPath = "LOCATION OF PYTHON SCRIPT OUTPUT CSV"

data = read.csv(paste0(projectPath,
                       "combo70Cgm3CarbAndBasalWithBgAtBolusRemovedPerDayStats-v5.csv"))

#Set Target Factors/Variables for analysis
target_factors = c(
  'totalDailyCarbs',
  'age',
  'diagnosisAge',
  'ISF_mgdL',
  'totalInsulin',
  'yearsLivingWithDiabetes'
)

target_factors_labels = c(
  "Total Daily Carbs",
  "Age",
  "Diagnosis Age",
  "Insulin Sensitivity Factor",
  "Total Daily Insulin",
  "Years Living w/ Diabetes"
)
fea = data[ , which(names(data) %in% target_factors) ]

target_vars = c(
  "percentBelow54.mgdL",
  "percentBelow70.mgdL",
  "percent70to180.mgdL",
  "percentAbove180.mgdL",
  "percentAbove250.mgdL"
)

gom = data[ , which(names(data) %in% target_vars) ]

target_vars_colors = range_colors = c("#D68174", "#FC9888", "#7BB895", "#CAAEFC", "#A18BC9")

#Set up functions for decision tree labeling
custom_node_labs <- function(x, labs, digits, varlen){
  str_hour_vals = sprintf("%.3f",24*x$frame$yval)
  hour_min_matrix = matrix(unlist(strsplit(str_hour_vals,".",fixed=TRUE)),nrow=2)
  hours = as.integer(unlist(hour_min_matrix[1,]))
  mins = as.character(round(as.double(hour_min_matrix[2,])/1000*60))
  ndays = c()
  ndonors = c()
  stat_text = c()
  
  for(node_var in 1:length(x$frame$var)){
    
    ndays = c(ndays, x$frame$n[node_var])
    
    if(x$frame$var[node_var]=="<leaf>"){
      ndonors = c(ndonors, length(unique(data[which(x$where==which(x$frame$n==ndays[node_var])),"hashID"])))
      stat_text = c(stat_text, paste("\nN Donors: ", ndonors[node_var], "\nN Days: ", ndays[node_var],sep=""))
    }else{
      ndonors=c(ndonors,"")
      stat_text = c(stat_text,"")
    }
  }

  paste(sprintf("%.1f",x$frame$yval*100),"%\n",hours,"h ", mins, "m", stat_text, sep="")
}


custom_node_color <- function(color_samples,current_gom){
  
  colorRampPalette(c("white",paste(target_vars_colors[which(target_vars == current_gom)])))(color_samples)
  
}

#Track each leaf node data statistics
collect_leaf_data <- function(image_name,tree_obj, gom_name, factor_name, factor_label){
  
  leaf_ids = sort(unique(tree_obj$where))
  
  for(id in 1:length(leaf_ids)){
    
    leafdonors = length(unique(data[which(tree_obj$where==leaf_ids[id]),"hashID"]))
    leafdays = nrow(data[which(tree_obj$where==leaf_ids[id]),])
    leafmin = min(data[,gom_name][which(tree_obj$where==leaf_ids[id])])
    leaf10perc = quantile(data[,gom_name][which(tree_obj$where==leaf_ids[id])],0.1)
    leaf25perc = quantile(data[,gom_name][which(tree_obj$where==leaf_ids[id])],0.25)
    leaf50perc = quantile(data[,gom_name][which(tree_obj$where==leaf_ids[id])],0.5)
    leaf75perc = quantile(data[,gom_name][which(tree_obj$where==leaf_ids[id])],0.75)
    leaf90perc = quantile(data[,gom_name][which(tree_obj$where==leaf_ids[id])],0.9)
    leafmax = max(data[,gom_name][which(tree_obj$where==leaf_ids[id])])
    leafmean = mean(data[,gom_name][which(tree_obj$where==leaf_ids[id])])
    leafsd = sd(data[,gom_name][which(tree_obj$where==leaf_ids[id])])
    
    if(factor_name == "mixed"){
      
      label_min = id
      leaf_label = paste("Group ", as.character(id),sep="")
      
    }else{
    
      label_min = min(data[which(tree_obj$where==leaf_ids[id]),factor_name])
      label_max = max(data[which(tree_obj$where==leaf_ids[id]),factor_name])
      
      if(label_max == max(data[,factor_name])){
        label_min = sprintf("%.1f",label_min)
        label_max = "+"
      }else{
        label_min = sprintf("%.1f",label_min)
        label_max = sprintf("-%.1f",label_max)
      }
      
      leaf_label = paste(label_min,label_max,sep="")
    }
    
    leaf_df = rbind(leaf_df,c(image_name,id,factor_label,leaf_label_min = label_min, leaf_label,leafdonors,leafdays,leafmin,leaf10perc,leaf25perc,leaf50perc,leaf75perc,leaf90perc,leafmax,leafmean,leafsd))
    
  }
  return(leaf_df)
}


###################### GENERATOR 0 #######################
################# Single Factor Trees ####################
#Finds all trees containing up to max_leaf_nodes
#By slowly increasing the complexity value (cp)

max_leaf_nodes = 6
leaf_df = data.frame("image_id"=NA,"leaf_num"=NA,"factor_label" = NA, "leaf_label_min" = NA,"leaf_label"=NA, "num_donors"=NA,"num_days"=NA,"min"=NA,"10perc"=NA,"25perc"=NA,"50perc"=NA,"75perc"=NA,"90perc"=NA,"max"=NA,"mean"=NA,"sd"=NA)
outputPath = "A:/single_factor_trees/percent70to180.mgdL/"
g = target_vars[3]
for(f in target_factors){
  
  equation = paste0("percent70to180.mgdL~",f)
  last_leaf_count = 1
  
  for(cp_val in seq(0.01,0.00001,-0.00001)){
   
    figureName = paste0("percent70to180.mgdL-", f, "-", as.character(round(cp_val,6)))
    
    tree.best=rpart(equation,
                    data = data,
                    method="anova",
                    control=rpart.control(minbucket=5000, cp=cp_val))
    
    if(!is.null(tree.best$splits)){
      # Round age, carbs, years with diabetes, and diagnosis Age up to whole numbers for display purposes only
      # (all other values remain consistent with original high precision split indices)
      tree.best$splits[which(rownames(tree.best$splits)=="totalDailyCarbs"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="totalDailyCarbs"),4]))
      tree.best$splits[which(rownames(tree.best$splits)=="age"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="age"),4]))
      tree.best$splits[which(rownames(tree.best$splits)=="yearsLivingWithDiabetes"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="yearsLivingWithDiabetes"),4]))
      tree.best$splits[which(rownames(tree.best$splits)=="diagnosisAge"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="diagnosisAge"),4]))
      
      # Round ISF and total Insulin indices to nearest 0.1 decimal point for display purposes only
      tree.best$splits[,4] = as.double(sprintf("%0.1f",tree.best$splits[,4]))
    }
    
    #cat(paste(as.character(round(cp_val,6)),"\n"))
    leaf_count = length(which(tree.best$frame$var=="<leaf>"))
    
    if(leaf_count > max_leaf_nodes){
      cat(paste("Max Leaf Nodes Exceeded! - Ending Current Factor Tree Search\n"))
      break
    }
    
    if(leaf_count > last_leaf_count){
      cat(paste("Found tree with ", as.character(leaf_count)," leaf nodes!", " (",figureName,")\n", sep=""))
      last_leaf_count = leaf_count
      
      png(file = paste0(outputPath, figureName,".png"),width=1920,height=1080,units="px",res = 300)
      #pdf(file=paste0(outputPath, figureName,".pdf"))
      rpart.plot(tree.best,type = 2,extra =  1,yesno=1,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(10,g), main=paste0(figureName))
      leaf_df=collect_leaf_data(paste0(figureName,".png"),tree.best,"percent70to180.mgdL",f,target_factors_labels[which(target_factors==f)])
      dev.off()
    }
    
    if(leaf_count == max_leaf_nodes){
      cat(paste("All trees found for this factor!\n"))
      break
    }
    
  }
  
}

#Write out leaf node statistics csv
leaf_df = leaf_df[-1,]
leaf_df = leaf_df[order(leaf_df$image_id),]
leaf_df$leaf_label = gsub(".0","",leaf_df$leaf_label,fixed=TRUE)
write.csv(leaf_df,file=paste0(projectPath,"leaf_node_information_v5.csv"),row.names = FALSE)

###################### GENERATOR 1 ########################
###################### Mixed Tree #########################

equation = paste0("percent70to180.mgdL~age+yearsLivingWithDiabetes+diagnosisAge")
last_leaf_count = 1
max_leaf_nodes = 20
leaf_df = data.frame("image_id"=NA,"leaf_num"=NA,"factor_label" = NA, "leaf_label_min" = NA,"leaf_label"=NA, "num_donors"=NA,"num_days"=NA,"min"=NA,"10perc"=NA,"25perc"=NA,"50perc"=NA,"75perc"=NA,"90perc"=NA,"max"=NA,"mean"=NA,"sd"=NA)
outputPath = "A:/mixed_factor_trees/percent70to180.mgdL/"
g = target_vars[3]

#for(cp_val in seq(0.1,0.00001,-0.00001)){
  #cp_val=.00113
  cp_val=.00183
  cat(paste0(cp_val,"\n"))
  figureName = paste0("percent70to180.mgdL-age+yearsLivingWithDiabetes+diagnosisAge", "-", as.character(round(cp_val,6)))
  
  tree.best=rpart(equation,
                  data = data,
                  method="anova",
                  control=rpart.control(minbucket=5000, cp=cp_val))
  
  if(!is.null(tree.best$splits)){
    # Round age, carbs, years with diabetes, and diagnosis Age up to whole numbers for display purposes only
    # (all other values remain consistent with original high precision split indices)
    tree.best$splits[which(rownames(tree.best$splits)=="totalDailyCarbs"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="totalDailyCarbs"),4]))
    tree.best$splits[which(rownames(tree.best$splits)=="age"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="age"),4]))
    tree.best$splits[which(rownames(tree.best$splits)=="yearsLivingWithDiabetes"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="yearsLivingWithDiabetes"),4]))
    tree.best$splits[which(rownames(tree.best$splits)=="diagnosisAge"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="diagnosisAge"),4]))
    
    # Round ISF and total Insulin indices to nearest 0.1 decimal point for display purposes only
    tree.best$splits[,4] = as.double(sprintf("%0.1f",tree.best$splits[,4]))
  }
  
  #cat(paste(as.character(round(cp_val,6)),"\n"))
  leaf_count = length(which(tree.best$frame$var=="<leaf>"))
  
  if(leaf_count > max_leaf_nodes){
    cat(paste("Max Leaf Nodes Exceeded! - Ending Current Factor Tree Search\n"))
    break
  }
  
  if(leaf_count > last_leaf_count){
    cat(paste("Found tree with ", as.character(leaf_count)," leaf nodes!", " (",figureName,")\n", sep=""))
    last_leaf_count = leaf_count
    
    png(file = paste0(outputPath, figureName,".png"),width=1920,height=1080,units="px",res = 300)
    rpart.plot(tree.best,type = 2,extra =  1,yesno=1,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(10,g), main=paste0(figureName))
    leaf_df=collect_leaf_data(paste0(figureName,".png"),tree.best,"percent70to180.mgdL","mixed","Group #")
    dev.off()
    
    #pdf(file=paste0(outputPath, figureName,".pdf"))
    #rpart.plot(tree.best,type = 2,extra =  1,yesno=1,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(10,g), main=paste0(figureName))
    #dev.off()
  }
  
  if(leaf_count == max_leaf_nodes){
    cat(paste("All trees found for this factor!\n"))
    break
  }
  
#}


#Write out leaf node statistics csv
leaf_df = leaf_df[-1,]
leaf_df = leaf_df[order(leaf_df$image_id),]
leaf_df$leaf_label = gsub(".0","",leaf_df$leaf_label,fixed=TRUE)
write.csv(leaf_df,file=paste0(projectPath,"leaf_node_mixed_tree_v5.csv"),row.names = FALSE)


########## GENERATOR 2 ###############
################# Create large sweep of 2-way interaction trees ###################
leaf_df = data.frame("image_id"=NA,"leaf_num"=NA,"factor_label" = NA, "leaf_label_min" = NA,"leaf_label"=NA, "num_donors"=NA,"num_days"=NA,"min"=NA,"10perc"=NA,"25perc"=NA,"50perc"=NA,"75perc"=NA,"90perc"=NA,"max"=NA,"mean"=NA,"sd"=NA)

for (g in colnames(gom)[3]){
  i = 1
  for (f in colnames(fea)){
    i = i+1
    for (f2 in colnames(fea)[2:length(fea)]){
      for(cp in c(0.01, 0.005, 0.001)){
        if(f != f2){
          figureName = paste0(g, "-", f, "-", f2, "-", toString(cp))
          equation = paste0(g, " ~ ", f, " + ", f2)
          tree.best=rpart(equation,
                          data = data,
                          method="anova",
                          control=rpart.control(minbucket=5000, cp=cp))
          # postscript(file = paste0(outputPath, g, "/eps/", figureName, ".eps"))
          
          # Round age, carbs, years with diabetes, and diagnosis Age up to whole numbers for display purposes only
          # (all other values remain consistent with original high precision split indices)
          tree.best$splits[which(rownames(tree.best$splits)=="totalDailyCarbs"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="totalDailyCarbs"),4]))
          tree.best$splits[which(rownames(tree.best$splits)=="age"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="age"),4]))
          tree.best$splits[which(rownames(tree.best$splits)=="yearsLivingWithDiabetes"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="yearsLivingWithDiabetes"),4]))
          tree.best$splits[which(rownames(tree.best$splits)=="diagnosisAge"),4] = as.double(ceiling(tree.best$splits[which(rownames(tree.best$splits)=="diagnosisAge"),4]))
          
          # Round ISF and total Insulin indices to nearest 0.1 decimal point for display purposes only
          tree.best$splits[,4] = as.double(sprintf("%0.1f",tree.best$splits[,4]))
          
          png(file = paste0(outputPath, g, "/", figureName, ".png"),width=5,height=5,units="in",res=300,pointsize = 1/300)
          rpart.plot(tree.best,digits=4,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(20,g),main=paste0(g, "-\n", f, "-", f2, "-", toString(cp)))
          leaf_df=collect_leaf_data(paste0(figureName, ".png"),tree.best,g)
          #title(figureName)
          dev.off()
        }
      }
    }
  }
}

snipped_tree <- rpart.plot(tree.best,snip=TRUE,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(20,g),main=paste0(g, "-\n", f, "-", f2, "-", toString(cp)))$obj
rpart.plot(snipped_tree,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(20,g),main=paste0(g, "-\n", f, "-", f2, "-", toString(cp)))


############## Generator 3 ####################
#Find all trees containing at least 1 additional factor in each tree
#By slowly increasing the complexity value (cp)
cp_val = .1
factor_count = length(target_factors)
last_counter = 0
cp_tracker = c()
decrease_rate = 0.8
factor_names = list()

for(r in 1:100){
  tree.best=rpart(percent70to180.mgdL~totalDailyCarbs+age+diagnosisAge+ISF_mgdL+totalInsulin+yearsLivingWithDiabetes,
                  data = data,
                  method="anova",
                  control=rpart.control(minbucket=1000, cp=cp_val))
  
  factors_present = length(unique(tree.best$frame$var[which(tree.best$frame$var!="<leaf>")]))
  
  if(factors_present>last_counter){
    cat(paste("Found Tree with ", factors_present, " factors with cp = ", cp_val, "\n", sep=""))
    factor_names[[factors_present]] = paste(as.character(unique(tree.best$frame$var[which(tree.best$frame$var!="<leaf>")])),collapse=" + ")
    cp_tracker = c(cp_tracker, cp_val)
    last_counter = factors_present
  }
  
  if(factors_present == factor_count){
    cat(paste("Found all trees in ", r," tries!",sep=""))
    break
  }
  
  cp_val = cp_val*decrease_rate
}

leaf_df = data.frame("image_id"=NA,"leaf_num"=NA,"factor_label" = NA, "leaf_label_min" = NA,"leaf_label"=NA, "num_donors"=NA,"num_days"=NA,"min"=NA,"10perc"=NA,"25perc"=NA,"50perc"=NA,"75perc"=NA,"90perc"=NA,"max"=NA,"mean"=NA,"sd"=NA)

#Start output of decision tree files
for(factor_num in 1:length(cp_tracker)){
  
  figureName = paste0(factor_num, "_factors_percent70to180.mgdL")
  
  tree.best=rpart(percent70to180.mgdL~totalDailyCarbs+age+diagnosisAge+ISF_mgdL+totalInsulin+yearsLivingWithDiabetes,
                  data = data,
                  method="anova",
                  control=rpart.control(minbucket=1000, cp=cp_tracker[factor_num]))
  
  png(file = paste0(outputPath, figureName,".png"),width=1920,height=1080,units="px",res = 300)
  pdf(file=paste0(outputPath, figureName,".pdf"))
  rpart.plot(tree.best,type = 2,extra =  1,yesno=1,left=FALSE,node.fun=custom_node_labs,box.palette=custom_node_color(10,g), main=paste0(figureName,"\n",factor_names[[factor_num]],"\n cp= ", round(cp_tracker[factor_num],5)))
  leaf_df=collect_leaf_data(paste0(figureName,".png"),tree.best,"percent70to180.mgdL")
  dev.off()
  
}

#Write out leaf node statistics csv
leaf_df = leaf_df[-1,]
leaf_df = leaf_df[order(leaf_df$image_id),]
write.csv(leaf_df,file=paste0(projectPath,"leaf_node_information_v3.csv"),row.names = FALSE)

############### Distribution Plots For Leaf Nodes #####################


#unique_carb_timestamps = sort(unique(carb_timestamp_hours))
#unique_bg_timestamps = sort(unique(big.timestamp_hours))

#meanBG_timeofday = c()
#mean_carbs_timeofday = c()
#count_carbs_timeofday = c()

#for(k in 1:length(unique_carb_timestamps)){
#  mean_carbs_timeofday=c(mean_carbs_timeofday,mean(all_carb_entries[which(carb_timestamp_hours==unique_carb_timestamps[k])]))
#  count_carbs_timeofday = c(count_carbs_timeofday, length(which(carb_timestamp_hours==unique_carb_timestamps[k])))
#  meanBG_timeofday = c(meanBG_timeofday,mean(big.bg[which(big.timestamp_hours==unique_carb_timestamps[k])]))
#}

#x_hour_format = format( seq.POSIXt(as.POSIXct(Sys.Date()), as.POSIXct(Sys.Date()+1), by = "2 hours"), "%H:%M", tz="UTC")
#carb_bin_format = format( seq.POSIXt(as.POSIXct(Sys.Date()), as.POSIXct(Sys.Date()+1), by = "30 min"), "%H:%M", tz="UTC")
#carb_count_formatted = c()
#carb_bin_intervals = findInterval(sort(as.numeric(as.factor(carb_timestamp_hours))),which(unique_carb_timestamps %in% carb_bin_format))
#carb_bins = unique_carb_timestamps[which(unique_carb_timestamps %in% carb_bin_format)]
#for(val in 1:length(unique(carb_bin_intervals))){
#  carb_count_formatted= c(carb_count_formatted,length(which(carb_bin_intervals==val)))
#}


leaf_count = c(1:2)

ggplot() + 
  #geom_col(aes(x=leaf_count,y=carb_count_formatted),width = 4,fill="#ffd382")+
  geom_rect()
  geom_point(aes(x=unique_carb_timestamps,y=(meanBG_timeofday-0.8*min(meanBG_timeofday))*350),color="#7bb895")+
  theme_classic()+
  theme(legend.position="none")+
  xlab("Time of Day (HH:MM)")+
  ylab("Total Carb Entry Count")+ 
  labs(title="Average BG vs Carb Entry Distribution")+
  scale_x_discrete(limits=c(unique_carb_timestamps),breaks=x_hour_format)+
  scale_y_continuous(sec.axis = sec_axis(~./350+0.8*min(meanBG_timeofday) , name = "Blood Glucose (mg/dL)"),limits=c(0,1.5*max(carb_count_formatted)))+
  theme(plot.title = element_text(size=20,family="Nunito",face="bold",color="#454545",hjust=0))+
  theme(axis.title = element_text(size=20*(7/8),family="Roboto Mono",face="bold",color="#a1a1a1"))+
  theme(axis.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c"))+
  theme(axis.title.y = element_text(margin = margin(t = 0, r = 15, b = 0, l = 0)))+
  theme(axis.title.x = element_text(margin = margin(t = 15, r = 0, b = 0, l = 0)))+
  theme(axis.text.x = element_text(angle=90,hjust=1,vjust=0.5))+
  theme(axis.title.y.right = element_text(margin = margin(t = 0, r = 0, b = 0, l = 15)))

########### TREE OUTPUT ###########

distribution_path = "A:/single_factor_trees/percent70to180.mgdL"
setwd(distribution_path)  
#images_to_make = unique(leaf_df$image_id)
images_to_make = dir()

for(factor_count_id in 1:length(images_to_make)){
  d=leaf_df[which(leaf_df$image_id==images_to_make[factor_count_id]),]
  x_min = seq(0.05,.2*nrow(d),0.2)
  x_max = seq(.15,.2*nrow(d),0.2)
  median_width = (x_max-x_min)*0.725
  median_xmin = x_min+(x_max-x_min-median_width)/2
  median_xmax = x_max-(x_max-x_min-median_width)/2
  
  #png(file = paste(images_to_make[factor_count_id],"_distribution_v4.png",sep=""),width=757,height=800,units="px",res=200)
  
  ggplot(data = d) + 
    #scale_x_continuous(name="Leaf Group",limits=c(0,0.2*nrow(d)),breaks=(x_max+x_min)/2, labels=seq(1,nrow(d),1)) + 
    scale_x_continuous(name="Leaf Group",limits=c(0,0.2*nrow(d)),breaks=(x_max+x_min)/2, labels=seq(1,nrow(d),1)) + 
    #scale_y_continuous(name="% Time in Range",limits=c(0,1)) +
    geom_rect(mapping=aes(ymin=as.double(X10perc), ymax=as.double(X90perc),xmin=x_min,xmax=x_max), color=NA,fill="#d0d0d0")+
    geom_rect(mapping=aes(ymin=as.double(X25perc), ymax=as.double(X75perc),xmin=x_min,xmax=x_max), color=NA,fill="#A3A3A3") +
    geom_rect(mapping=aes(ymin=as.double(X50perc)-median_width/2, ymax=as.double(X50perc)+median_width/2,xmin=median_xmin,xmax=median_xmax), color="white",fill="#7BB895")+
    theme_classic()+
    theme(legend.position="none")+
    xlab("Time of Day (HH:MM)")+
    ylab("Time in Range %")+ 
    #labs(title="Average BG vs Carb Entry Distribution")+
    #scale_x_discrete(limits=c(0,0.2*nrow(d)),breaks=c("1","2"))+
    scale_y_continuous(sec.axis = sec_axis(~.*24, name = "Time in Range (hours)",breaks=seq(0,24,3)),limits=c(0,1),breaks=round(seq(0,1,1/8),2),labels=round(seq(0,100,100/8)))+
    theme(plot.title = element_text(size=20,family="Nunito",face="bold",color="#454545",hjust=0))+
    theme(axis.title = element_text(size=20*(7/8),family="Roboto Mono",face="bold",color="#a1a1a1"))+
    theme(axis.text = element_text(size=20*(2/3),family="Roboto Mono",face="bold",color="#7c7c7c"))+
    theme(axis.title.y = element_text(margin = margin(t = 0, r = 15, b = 0, l = 0)))+
    theme(axis.title.x = element_text(margin = margin(t = 15, r = 0, b = 0, l = 0)))+
    theme(axis.text.x = element_text(hjust=0.45))+
    theme(axis.title.y.right = element_text(margin = margin(t = 0, r = 0, b = 0, l = 15)))
  #geom_text(data=leaf_df, aes(xmin=X25perc,xmax=X75perc,ymin=1,ymax=2), size=4) 
  #print(p)
  #dev.off()
  
  ggsave(file=paste(images_to_make[factor_count_id],"_distribution_v4.png",sep=""), device="png", path=distribution_path, width=3.32+((nrow(d)-2)*0.8), height=5,dpi=300)
  ggsave(file=paste(images_to_make[factor_count_id],"_distribution_v4.svg",sep=""), device="svg", path=distribution_path, width=3.32+((nrow(d)-2)*0.8), height=5,dpi=300)
  
}
  
#ggsave(file=paste(factor_count_id,"_june2018_distribution_v1.svg",sep=""), device="svg", path="A:/", width=5*(0.2*nrow(d)), height=5, dpi=300, units="in")
#ggsave(file=paste(factor_count_id,"_june2018_distribution_v1.eps",sep=""), device="eps", path="A:/", width=5*(0.2*nrow(d)), height=5, dpi=300, units="in")

### Figure plotting example code

#d=data.frame(x1=c(1,3,1,5,4), x2=c(2,4,3,6,6), y1=c(1,1,4,1,3), y2=c(2,2,5,3,5), t=c('a','a','a','b','b'), r=c(1,2,3,4,5))
#ggplot() + 
#  scale_x_continuous(name="x") + 
#  scale_y_continuous(name="y") +
#  geom_rect(data=d, mapping=aes(xmin=x1, xmax=x2, ymin=y1, ymax=y2, fill=t), color="black", alpha=0.5)

#### Tree Split Functionality Check ####
#unique_ages = sort(unique(data$age))
#diff_tracker = c()
#for(p in 1:length(unique_ages)){
#  diff_tracker = c(diff_tracker, abs(mean(data$percent70to180.mgdL[which(data$age<unique_ages[p])])-mean(data$percent70to180.mgdL[which(data$age>=unique_ages[p])])))
#}
#plot(unique_ages,diff_tracker)
