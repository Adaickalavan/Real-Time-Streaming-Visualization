from bokeh.plotting import figure
from bokeh.models import LinearAxis, Range1d, HoverTool, ColumnDataSource, Legend
from bokeh.layouts import gridplot, column, row
from bokeh.models.widgets import CheckboxGroup, Div
from bokeh.io import curdoc
from tornado import gen

class Visual:
    def __init__(self, callbackFunc, running):
        self.text1 = Div(text="""<h1 style="color:blue">Visualization of Real Time Data Streaming</h1>""", width=900, height=50) # Text to be displayed at the top of the webpage
        self.running = running # Store the current state of the Flag
        self.callbackFunc = callbackFunc # Store the callback function
        self.hover = HoverTool(  # To show tooltip when the mouse hovers over the plot data        
                tooltips=[
                    ("index", "$index"), # Show index of plot data points
                    ("(x,y)", "(@x, $y)") # Show x and y coordinates of the plot data points
                ]
            )
        self.tools = "pan,box_zoom,wheel_zoom,reset" # Set pan, zoom, etc., options for the plot
        self.plot_options = dict(plot_width=800, plot_height=200, tools=[self.hover, self.tools]) # Set plot width, height, and other plot options
        self.updateValue = True # Internal state for updating of plots
        self.source, self.pAll = self.definePlot() # Define various plots. Return handles for data source (self.source) and combined plot (self.pAll)
        self.doc = curdoc() # Save curdoc() to make sure all threads see the same document. curdoc() refers to the Bokeh web document
        self.layout() # Set the checkboxes and overall layout of the webpage 
        self.prev_y1 = 0 

    def definePlot(self):
        # Define plot 1 to plot raw sensor data
        p1 = figure(**self.plot_options, title="Sensor Data")
        p1.yaxis.axis_label = "Sensor Value"
        # Define plot 2 to plot (1) processed sensor data and (2) classification result at each time point
        p2 = figure(**self.plot_options, x_range=p1.x_range, title="Computed Value") # Link x-axis of first and second graph
        p2.xaxis.axis_label = "Time (Discrete)"
        p2.yaxis.axis_label = "Computed Value"
        p2.extra_y_ranges = {"class": Range1d(start=-1, end=2)} # Add a secondary y-axis
        p2.add_layout(LinearAxis(y_range_name="class", axis_label="Classification"), 'right') # Name and place the secondary y-axis on the right vertical edge of the graph
        # Define source data for all plots
        source = ColumnDataSource(data=dict(x=[0], y1=[0], y2=[0], y3=[0]))
        # Define graphs for each plot
        r1 = p1.line(x='x', y='y1', source=source, color="firebrick", line_width=2) # Line plot for sensor raw data
        r1a = p1.circle(x='x', y='y1', source=source, color="firebrick", fill_color="white", size=8)  # Circles to indicate data points in first graph
        r2 = p2.line(x='x', y='y2', source=source, color="indigo", line_width=2) # Line plot for computed values
        r2a = p2.circle(x='x', y='y2', source=source, color="indigo", fill_color="white", size=8) # Circles to indicate data points in second graph
        r3 = p2.step(x='x', y='y3', source=source, color="green", line_width=2, y_range_name="class") # Overlay step plot for binary classes in the second graph
        # Place legends outside the plot area for each data source
        legend = Legend(items=[("Sensor Data", [r1, r1a])], location=(5, 30))
        p1.add_layout(legend, 'right')
        p1.legend.click_policy = "hide" # Plot line may be hidden by clicking the legend marker 
        legend = Legend(items=[("Computed Value", [r2, r2a]), ("Classification", [r3])], location=(5, 30))
        p2.add_layout(legend, 'right')
        p2.legend.click_policy = "hide"  # Plot line may be hidden by clicking the legend marker
        # Combine all plots into a gridplot for better vertical alignment
        pAll = gridplot([[p1], [p2]])

        return source, pAll # Return handles to data source and gridplot

    @gen.coroutine
    def update(self, val):
        if self.updateValue: # Update the plots only if the 'self.updateValue' is True
            # Compute new values for each column data
            newx = self.source.data['x'][-1] + 1 # Increment the time step on the x-axis of the graphs
            newy1 = val # Assign raw sensor data to be displayed in the first graph
            newy2 = (val + self.prev_y1)/2 # Perform computation (i.e., moving average) on the sensor data and plot in the second graph
            self.prev_y1 = newy1
            newy3 = newy2 > 5 # Classify the signal (i.e., binary calssification) at each time point and plot the results in the second graph
            # Construct the new values for all columns, and pass to stream
            new_data = dict(x=[newx], y1=[newy1], y2=[newy2], y3=[newy3])
            self.source.stream(new_data, rollover=20) # Feed new data to the graphs and set the rollover period to be xx samples

    def checkbox1Handler(self, attr, old, new):
        if 0 in list(new):  # Verify if the first checkbox is ticked currently
            if 0 not in list(old): # Perform actions if the first checkbox was not ticked previously, i.e., it changed state recently 
                self.running.set() # Set the Flag
                self.callbackFunc(self, self.running) # Restart the Sensor thread
        else:
            self.running.clear()  # Kill the Sensor thread by clearing the Flag
        if 1 in list(new):  # Verify if the second checkbox is ticked
            self.updateValue = True # Set internal value to continue updating the graphs
        else:
            self.updateValue = False # Set internal value to stop updating the graphs

    def layout(self):
        # Build interactive user interface
        checkbox1 = CheckboxGroup(labels=["Start/Stop Sensor Thread", "Start/Stop Plotting"], active=[0, 1]) # Create checkboxes
        checkbox1.on_change('active', self.checkbox1Handler) # Specify the action to be performed upon change in checkboxes' values 
        # Build presentation layout
        layout = column(self.text1, row(checkbox1, self.pAll)) # Place the text at the top, followed by checkboxes and graphs in a row below 
        self.doc.title = "Real Time Sensor Data Streaming" # Name of internet browser tab
        self.doc.add_root(layout) # Add the layout to the web document