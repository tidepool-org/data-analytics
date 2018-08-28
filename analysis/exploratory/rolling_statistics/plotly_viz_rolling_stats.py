#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
description: Plotly visualization of rolling statistics for Tidepool blood glucose 
             and insulin pump data.
version: 0.0.1
Created: 8/1/2018
author: Jason Meno
dependencies:
    * requires Tidepool user's datawith est.localTime
license: BSD-2-Clause

TODO:
    
"""

# %% Import Libraries
import pandas as pd
import numpy as np
from math import exp,pow
import datetime as dt
import os
import sys
import argparse
import json
import time
import matplotlib.pyplot as plt
import plotly.plotly as py
from plotly import tools
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
import cufflinks as cf

# %% Test Plotly Output
        
trace_high = go.Scatter(
    x=df['est.localTime_rounded'],
    y=df['30day_mean'],
    name = "30 Day Mean",
    line = dict(color = '#17BECF'),
    opacity = 0.8)

trace_low = go.Scatter(
    x=df['est.localTime_rounded'],
    y=df['24hr_mean'],
    name = "24 Hour Mean",
    line = dict(color = '#7F7F7F'),
    opacity = 0.8)

#data = [trace_high,trace_low]

layout = dict(
    title='Time Series with Rangeslider',
    xaxis=dict(
        rangeselector=dict(
            buttons=list([
                dict(count=1,
                     label='1d',
                     step='day',
                     stepmode='backward'),
                dict(count=7,
                     label='7d',
                     step='day',
                     stepmode='backward'),
                dict(count=1,
                     label='1m',
                     step='month',
                     stepmode='backward'),
                dict(count=3,
                     label='3m',
                     step='month',
                     stepmode='backward'),
                dict(count=6,
                     label='6m',
                     step='month',
                     stepmode='backward'),
                dict(count=1,
                     label='1y',
                     step='year',
                     stepmode='backward'),

                 
                dict(step='all')
            ])
        ),
        rangeslider=dict(
            visible = True
        ),
        type='date'
    )
)

fig = tools.make_subplots(rows=2, cols=1)

fig.append_trace(trace_low, 1, 1)
fig.append_trace(trace_high, 2, 1)
#fig.append_trace(trace_low, 3, 1)
fig['layout'] = layout

#fig = dict(data=data, layout=layout)
plot(fig)
    
#%% Slider Example

rolling_prefixes = ["15min","1hr","2hr","6hr","8hr","12hr","24hr",
                        "7day","14day","30day","90day","1year"]

data = [dict(
        visible = False,
        line=dict(color='#00CED1', width=1),
        name = str(prefix)+" Moving Average",
        x = cgm_df["est.localTime_rounded"],
        y = cgm_df[prefix+"_mean"]) for prefix in rolling_prefixes]
        
#trace2 = [dict(
#        visible = False,
#        line=dict(color='#00CED1', width=1),
#        name = str(prefix)+" Moving Average",
#        x = cgm_df["est.localTime_rounded"],
#        y = cgm_df[prefix+"_a1c"]) for prefix in rolling_prefixes]
        
#data = [trace1, trace2]
        
data[5]['visible'] = True

#plot(data)

steps = []


for i in range(len(data)):
    step = dict(
        method = 'restyle',  
        args = ['visible', [False] * len(data)],
        label = rolling_prefixes[i]
    )
    step['args'][1][i] = True # Toggle i'th trace to "visible"
    steps.append(step)
    
sliders = [dict(
    active = 10,
    currentvalue = {"prefix": "Moving Average Size: "},
    #pad = {"t": 50},
    steps = steps,
    
    #PLACEMENT
    x = 0.15,
    y = 0,
    len = 0.85,
    pad = dict(t = 20, b = 0),
    yanchor = "bottom",
    xanchor = "left",
)]

#layout = dict(sliders=sliders)

layout = dict(
    title='Tidepool Rolling Statistics',

    # GENERAL LAYOUT
    #width = 1080,
    #height = 720,
    #autosize = True,
    #font = dict(
    #    family = "Overpass",
    #    size = 12,
    #),
    margin = dict(
        t = 80,
        l = 50,
        b = 50,
        r = 50,
        pad = 5,
    ),
            
    sliders=sliders,
    
    
    xaxis=dict(
        rangeselector=dict(
            buttons=list([
                dict(count=1,
                     label='1d',
                     step='day',
                     stepmode='backward'),
                dict(count=7,
                     label='7d',
                     step='day',
                     stepmode='backward'),
                dict(count=1,
                     label='1m',
                     step='month',
                     stepmode='backward'),
                dict(count=3,
                     label='3m',
                     step='month',
                     stepmode='backward'),
                dict(count=6,
                     label='6m',
                     step='month',
                     stepmode='backward'),
                dict(count=1,
                     label='1y',
                     step='year',
                     stepmode='backward'),
                dict(step='all')
            ])
        ),
        
        rangeslider=dict(
            visible = True
        ),
        type='date'
    )
)
        
#fig = tools.make_subplots(rows=3, cols=1)

#fig.append_trace(data, 1, 1)
#fig.append_trace(trace_high, 2, 1)
#fig.append_trace(trace_low, 3, 1)
#fig['layout'] = layout

fig = dict(data=data, layout=layout)
plot(fig)

# %% Tabbed Updating Layout

trace_day = go.Scatter(
                x=dayStats["endTime.day"],
                y=dayStats["mean_mgdL.day"],
                name = "Daily Avg",
                visible = "legendonly",
                line = dict(color = '#eff3ff'),
                )

trace_week = go.Scatter(
                x=dayStats["endTime.week"],
                y=dayStats["mean_mgdL.week"],
                name = "Weekly Avg",
                line = dict(color = '#bdd7e7'),
                )

trace_month = go.Scatter(
                x=dayStats["endTime.month"],
                y=dayStats["mean_mgdL.month"],
                name = "Monthly Avg",
                visible = "legendonly",
                line = dict(color = '#6baed6'),
                )

trace_quarter = go.Scatter(
                x=dayStats["endTime.quarter"],
                y=dayStats["mean_mgdL.quarter"],
                name = "3-month Avg",
                line = dict(color = '#3182bd'),
                )

trace_year = go.Scatter(
                x=dayStats["endTime.year"],
                y=dayStats["mean_mgdL.year"],
                name = "Yearly Avg",
                line = dict(color = '#08519c'),
                )

plotlyData = [trace_day, trace_week, trace_month, trace_quarter, trace_year]

def getDataByButton(metricName):
    global dayStats
    # return arg list to set x, y and chart title

    return [{'y':[dayStats[metricName + ".day"],
                  dayStats[metricName + ".week"],
                  dayStats[metricName + ".month"],
                  dayStats[metricName + ".quarter"],
                  dayStats[metricName + ".year"]
           ]}, {'title':metricName} ]

updatemenus=list([
            dict(
                buttons=list([   
                    dict(label = 'Average mg/dL',
                         method = 'update', 
                         args=getDataByButton('mean_mgdL')
                    ),
                    dict(label = 'Time in Range',
                         method = 'update', 
                         args=getDataByButton('percentTimeInRange')
                    ),  
                    dict(label = 'Time Below 70 mg/dL',
                         method = 'update', 
                         args=getDataByButton('percentBelow70')
                    ),
                    dict(label = 'Time Above 250 mg/dL',
                         method = 'update', 
                         args=getDataByButton('percentAbove250')
                    ), 
                    dict(label = 'COV',
                         method = 'update', 
                         args=getDataByButton('cov_mgdL')
                    ), 
                ]),
                direction = 'left',
                pad = {'r': 10, 't': 10},
                showactive = True,
                type = 'buttons',
                x = 0.1,
                xanchor = 'left',
                y = 1.1,
                yanchor = 'top' 
            )
        ])

#
#updatemenus = list([
#    dict(type="buttons",
#         buttons=list([   
#            dict(label = 'Daily Avg',
#                 method = 'restyle',
#                 args = ['visible', True]),
#            dict(label = 'Weekly Avg',
#                 method = 'restyle',
#                 args = ['visible[1]', False]),
#            dict(label = 'Monthly Avg',
#                 method = 'restyle',
#                 args = ['visible[2]', False]),
#            dict(label = '3-Month Avg',
#                 method = 'restyle',
#                args = ['visible[3]', False]),
#            dict(label = 'Yearly Avg',
#                 method = 'restyle',
#                args = ['visible[4]', False])
#        ]),
#    )
#])


layout = dict(
    title = "Average CBG Levels over Different Time Periods",
    updatemenus=updatemenus,
#    yaxis = dict(
#        range = [70, 140])
)


fig = dict(data=plotlyData, layout=layout)
plot(fig, filename = "Average CBG Levels over Different Time Periods")

#%% Shared X-Axis (24-HOUR DATA)

#from plotly import tools
#import plotly.plotly as py
#import plotly.graph_objs as go
#cgm_df.set_index("est.localTime_rounded",inplace=True)
#bolus_df.set_index("est.localTime_rounded",inplace=True)
#basal_df.set_index("est.localTime_rounded",inplace=True)
#iob_df.set_index("est.localTime_rounded",inplace=True)

#cgm_df = cgm_df.loc['2016-12-16 00:00:00':'2016-12-30 23:55:00']
#bolus_df = bolus_df.loc['2016-12-16 00:00:00':'2016-12-30 23:55:00']
#basal_df = basal_df.loc['2016-12-16 00:00:00':'2016-12-30 23:55:00']
#iob_df = iob_df.loc['2016-12-16 00:00:00':'2016-12-30 23:55:00']

def get_color(value):
    if value >250:
        return "#A18BC9"
    elif value>180:
        return "#CAAEFC"
    elif value <54:
        return "#D68174"
    elif value <70:
        return "FC9888"
    else:
        return "#7BB895"  
        
trace_cgm = go.Scatter(
    x=cgm_df.index,
    y=cgm_df["mg_dL"],
    name="mg/dL",
    mode='markers',
    marker = dict(color=[get_color(val) for val in cgm_df["mg_dL"]])
)
trace_iob = go.Scatter(
    x=iob_df.index,
    y=iob_df["iob"],
    name="u"
)
trace_bolus = go.Scatter(
    x=bolus_df.index,
    y=bolus_df["normal"],
    mode='markers',
    name="u"
)
trace_basal = go.Scatter(
    x=basal_df.index,
    y=basal_df["rate"],
    name="u/Hr"
)
fig = tools.make_subplots(rows=4, cols=1, specs=[[{}], [{}], [{}], [{}]],
                          shared_xaxes=True, shared_yaxes=False,
                          vertical_spacing=.01,
                          subplot_titles=('CGM', 'Insulin On Board','Bolus','Basal'))
fig.append_trace(trace_cgm, 1, 1)
fig.append_trace(trace_iob, 2, 1)
fig.append_trace(trace_bolus, 3, 1)
fig.append_trace(trace_basal, 4, 1)

#fig['layout']['xaxis1'].update(title='Blood Glucose (mg/dL)')
#fig['layout']['xaxis2'].update(title='Bolus Insulin (units)')
#fig['layout']['xaxis3'].update(title='Basal Insulin (units/hour)')

fig['layout']['yaxis1'].update(title='Blood Glucose (mg/dL)',range=[cgm_df.mg_dL.min(),cgm_df.mg_dL.max()])
fig['layout']['yaxis2'].update(title='Insulin On Board (units)', range=[0, iob_df.iob.max()])
fig['layout']['yaxis3'].update(title='Bolus Insulin (units)', range=[bolus_df.normal.min(), bolus_df.normal.max()])
fig['layout']['yaxis4'].update(title='Basal Insulin (units/hour)',range=[basal_df.rate.min(),basal_df.rate.max()])

#fig['layout']['xaxis1'].update(linecolor='black',mirror=True)
#fig['layout']['xaxis2'].update(linecolor='black',mirror=True)
#fig['layout']['xaxis3'].update(linecolor='black',mirror=True)

fig['layout'].update(title='Rolling Stats Continuous Subplots')
plot(fig, filename='example-rolling-stats-with-iobs.html')

#%% Shared X-Axis (CONTINUOUS DATA)

#from plotly import tools
#import plotly.plotly as py
#import plotly.graph_objs as go

def get_color(value):
    if value >250:
        return "#A18BC9"
    elif value>180:
        return "#CAAEFC"
    elif value <54:
        return "#D68174"
    elif value <70:
        return "#FC9888"
    else:
        return "#7BB895"  
        
trace_cgm_24hr = go.Scatter(
    x=cgm_daily.index,
    y=cgm_daily["24hr_cgm_mean"],
    name="24hr CGM Mean",
    mode='lines'
    #marker = dict(color='blue')
)

trace_cgm_7day = go.Scatter(
    x=cgm_daily.index,
    y=cgm_daily["7day_cgm_mean"],
    name="7day CGM Mean",
    mode='lines'
    #marker = dict(color='blue')
)

trace_cgm_below70 = go.Bar(
        x=cgm_daily.index,
        y=cgm_daily["7day_cgm_percentBelow70"],
        name="24hr <70",
        marker=dict(color="#FC9888")
)
trace_cgm_in_range = go.Bar(
        x=cgm_daily.index,
        y=cgm_daily["7day_cgm_percentTimeInRange"],
        name="24hr Time in Range",
        marker=dict(color="#7BB895")
)
trace_cgm_above180 = go.Bar(
        x=cgm_daily.index,
        y=cgm_daily["7day_cgm_percentAbove180"],
        name="24hr >180",
        marker=dict(color="#CAAEFC")
)
trace_bolus = go.Scatter(
    x=bolus_daily.index,
    y=bolus_daily["24hr_bolus_mean"],
    name="u"
)
trace_basal = go.Scatter(
    x=basal_daily.index,
    y=basal_daily["24hr_basal_mean"],
    name="u/Hr"
)
fig = tools.make_subplots(rows=3, cols=1, specs=[[{}], [{}], [{}]],
                          shared_xaxes=True, shared_yaxes=False,
                          vertical_spacing=.1,
                          subplot_titles=('CGM', 'Bolus','Basal'))



def get_window_color(value, val_type):
    
    if val_type == "cgm":
        if value == "24hr":
            return "#eff3ff"
        elif value == "7day":
            return "#bdd7e7"
        elif value == "14day":
            return "#6baed6"
        elif value == "30day":
            return "#3182bd"
        elif value == "90day":
            return "#08519c"
        else:
            return "#02356b"  
    elif val_type == "bolus":
        if value == "24hr":
            return "#c9e5ed"
        elif value == "7day":
            return "#a6deed"
        elif value == "14day":
            return "#87d8ed"
        elif value == "30day":
            return "#5acbe8"
        elif value == "90day":
            return "#21c8f2"
        else:
            return "#00c5f7" 
    else:
        if value == "24hr":
            return "#abc2c9"
        elif value == "7day":
            return "#85b4c1"
        elif value == "14day":
            return "#68a8ba"
        elif value == "30day":
            return "#4a9bb2"
        elif value == "90day":
            return "#2897b7"
        else:
            return "#0098c4" 
    
metrics = []
metric_type = []
cgm_metrics = []
for metric in list(cgm_daily)[16:len(list(cgm_daily))]:

    metrics.append(metric.split('_')[2])
    cgm_metrics.append(metric.split('_')[2])
    metric_type.append('cgm')
    trace_cgm = go.Scatter(
        x=cgm_daily.index,
        y=cgm_daily[metric],
        name="CGM "+metric.split('_')[0],
        mode='lines',
        visible=True if metric.split('_')[2]=="mean" else False,
        line = dict(color=get_window_color(metric.split('_')[0],"cgm"))
    #marker = dict(color='blue')
    )
    fig.append_trace(trace_cgm, 1, 1)

bolus_metrics = []  
for metric in list(bolus_daily)[15:len(list(bolus_daily))]:

    metrics.append(metric.split('_')[2])
    bolus_metrics.append(metric.split('_')[2])
    metric_type.append('bolus')
    trace_bolus = go.Scatter(
        x=bolus_daily.index,
        y=bolus_daily[metric],
        name="BOLUS "+metric.split('_')[0],
        mode='lines',
        visible=True if metric.split('_')[2]=="mean" else False,
        line = dict(color=get_window_color(metric.split('_')[0],"bolus"))
    #marker = dict(color='blue')
    )
    fig.append_trace(trace_bolus, 2, 1)
    
basal_metrics = []  
for metric in list(basal_daily)[15:len(list(basal_daily))]:

    metrics.append(metric.split('_')[2])
    basal_metrics.append(metric.split('_')[2])
    metric_type.append('basal')
    trace_basal = go.Scatter(
        x=basal_daily.index,
        y=basal_daily[metric],
        name="BASAL "+metric.split('_')[0],
        mode='lines',
        visible=True if metric.split('_')[2]=="mean" else False,
        line = dict(color=get_window_color(metric.split('_')[0],"basal"))
    #marker = dict(color='blue')
    )
    fig.append_trace(trace_basal, 3, 1)
 
#fig.append_trace(trace_cgm1, 1, 1)
#fig.append_trace(trace_cgm2, 1, 1)
#fig.append_trace(trace_bolus, 2, 1)
#fig.append_trace(trace_basal, 3, 1)
#fig.append_trace(trace_cgm_below70, 1, 1)
#fig.append_trace(trace_cgm_in_range, 1, 1)
#fig.append_trace(trace_cgm_above180, 1, 1)

#fig['layout']['xaxis1'].update(title='Blood Glucose (mg/dL)')
#fig['layout']['xaxis2'].update(title='Bolus Insulin (units)')
#fig['layout']['xaxis3'].update(title='Basal Insulin (units/hour)')

#WITH RANGE
#fig['layout']['yaxis1'].update(title='Blood Glucose (mg/dL)',range=[cgm_daily["24hr_cgm_mean"].min(),cgm_daily["24hr_cgm_mean"].max()])
#fig['layout']['yaxis2'].update(title='Bolus Insulin (units)', range=[bolus_daily["24hr_bolus_mean"].min(), bolus_daily["24hr_bolus_mean"].max()])
#fig['layout']['yaxis3'].update(title='Basal Insulin (units/hour)',range=[basal_daily["24hr_basal_mean"].min(),basal_daily["24hr_basal_mean"].max()])

currentVisibility = ["mean"==metrics[j] for j in range(len(metrics))]
visibility_list = []
visibility_list.append(currentVisibility)
def updateVisibility(var_type, metric):
    
    global currentVisibility
    global metrics
    global visibility_list
    

    currentVisibility = [metric==metrics[j] for j in range(len(cgm_metrics))]
    
        
    #to_set_true = []
    #if(var_type=='cgm'):
    #    
    #    for j in range(0,len(cgm_metrics)):
    #        currentVisibility[j] = False
    #        
    #        if(metrics[j]==metric):
    #            to_set_true.append(j)
    #    
    #    for j in to_set_true:
    #        currentVisibility[j] = True
   # 
    #if(var_type=="bolus"):
    #    for j in range(len(cgm_metrics),(len(cgm_metrics)+len(bolus_metrics))):
    #        currentVisibility[j] = False
    #        
    #        if(metrics[j]==metric):
    #                to_set_true.append(j)
    #    
    #    for j in to_set_true:
    #        currentVisibility[j] = True
    #else:
    #    for j in range((len(cgm_metrics)+len(bolus_metrics)),((len(cgm_metrics)+len(bolus_metrics))+len(basal_metrics))):
    #        currentVisibility[j] = False
    #        
    #        if(metrics[j]==metric):
    #                to_set_true.append(j)
    #    
    #    for j in to_set_true:
    #        currentVisibility[j] = True
            
    #visibility_list.append(currentVisibility)
    return currentVisibility
    
        
### Create buttons for drop down menu
buttons1 = []
for metric in set(cgm_metrics):
    
    button = dict(
                 label =  metric,
                 method = 'update',
                 args = [{'visible': updateVisibility('cgm',metric)}])
    
    buttons1.append(button)
    
buttons2 = []
for metric in set(bolus_metrics):
    
    button = dict(
                 label =  metric,
                 method = 'update',
                 args = [{'visible': updateVisibility('bolus',metric)}])
    
    buttons2.append(button)

buttons3 = []
for metric in set(basal_metrics):
    
    button = dict(
                 label =  metric,
                 method = 'update',
                 args = [{'visible': updateVisibility('basal',metric)}])
    
    buttons3.append(button)

updatemenus = list([
    dict(active=1,
         x=-0.05,
         y=0.9,
         buttons=buttons1,
         #type='buttons'
         #type='buttons'
         ),
    dict(active=1,
         x=-0.05,
         y=0.5,
         buttons=buttons2
         #type='buttons'
         ),
    dict(active=1,
         x=-0.05,
         y=0.1,
         buttons=buttons3
         #type='buttons'
         )
])
    
#WITHOUT RANGE
fig['layout']['yaxis1'].update(title='Blood Glucose (mg/dL)')
fig['layout']['yaxis2'].update(title='Bolus Insulin (units)')
fig['layout']['yaxis3'].update(title='Basal Insulin (units/hour)')

def getDataByButton(metricName):
    #global dayStats
    # return arg list to set x, y and chart title
    
    #return [{'y':[dayStats[metricName + ".day"],
    #              dayStats[metricName + ".week"],
    #              dayStats[metricName + ".month"],
    #              dayStats[metricName + ".quarter"],
    #              dayStats[metricName + ".year"]
    #       ]}, {'title':metricName} ]
    return
    

#fig['layout']['xaxis1'].update(linecolor='black',mirror=True)
#fig['layout']['xaxis2'].update(linecolor='black',mirror=True)
#fig['layout']['xaxis3'].update(linecolor='black',mirror=True)

fig['layout'].update(title='Rolling Stats Continuous Subplots',barmode='stack')
fig['layout']['updatemenus'] = updatemenus
plot(fig, filename='example-rolling-stats-basic.html')