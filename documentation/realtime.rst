.. raw:: latex

    \clearpage

.. _realtime_simulation:

Realtime simulation
===============================

Realtime simulations are intended for use with external simulation
software, such as cyber security simulations or linked energy/water
simulations. In these scenarios, WNTR is being used to provide the 
"ground truth" for the physical system state. In other words, WNTR
is being modified by external commands, not by the typical internal
rules or controls that are included in the WaterNetworkModel.

One item to note is that "realtime" does not necessarily require the
model to be run at wallclock rate. It merely indicates that WNTR is
running each hydraulic step with a call to an external function to
determine when to proceed, which allows this external function to 
synchronize WNTR's simulation clock with a different simulation's 
clock.

The main issue to consider in the realtime paradigm is that most of
the work is "someone else's problem"; i.e., WNTR does not provide 
a class that will communicate with a simulated industrial control
system, the user must code that piece themselves. Likewise, in the
case of a cyber attack siimulation, WNTR is *not* the piece that is 
being attacked. All WNTR does is provide the "real world" state of 
the WDS.

Take the following example - as part of a cyber attack simulation, 
a researcher wants to use WNTR as the hydraulic simulator. Using the
realtime WNTR module, the researcher can write a class that will 
read commands from some source, a database e.g., and WNTR will 
respond with the system state if those commands were given. If the 
attack is supposed to disrupt those commands, then it is the database
that would be attacked, not the WNTR simulation. The attack would
prevent WNTR from ever getting the message rather than trying to 
send some different value to WNTR itself.

As a second example, examine a linked energy/water simulation 
framework. The WDS hydraulic model needs to react to changes in the
electrical grid status - particularly power outages that might 
impact pumps and control systems. The user would code a class or 
classes that take input from the electrical grid simulation and
apply a suite of controls that turn off a pump and sensors at a 
specific location. When power is restored, that class would then
apply different rules in response to values that it sees in the 
WNTR simluation. The same class or classes could also report back
to the electrical grid simulation the current power usage by 
pumps in the WDS, allowing for a more dynamic coupling between the
electrical and hydraulic models.

WNTR realtime API
-----------------

First, let us assume that the user has written a connection class
that will act as the messenger between their external simulator
and WNTR, and let us call that class ``UserICSLink`` and the object
itself ``myicslink``.

The `wntr.sim.realtime` module contains RealtimeSimulator classes that 
have a specific API allowing the user to attach callback hooks 
for reading, writing, and synchronizing the simulation. The API
is as simple and generic as possible to provide maximum flexibility
to the user integrating the WNTR simulation.

The first step is to define the ICS touchpoints. Specifically, this
means identifying and naming the ICS instruments and their WNTR
WaterNetworkModel equivalents. For example, if there is a pressure 
sensor in the real world that is attached to the ICS at tank "1",
then the user must tell the RealtimeSimulator that such a sensor
exists and to report values from that object. Likewise, if the ICS
can set the pump status for pump "1", then the RealtimeSimulator
needs to know to report and accept changes for that pump. Unlike in
WNTR and EPANET, the names of sensors need to be unique across all
nodes and links (just like in a real ICS), so the touchpoints are
renamed during this process.

For example:

.. code:: python

    wn = WaterNetworkModel("myWDSmodel.inp")
    sim = RealtimeSimulator(wn)
    sim.add_sensor_instrument('MyTankPressure', 'node', '1', 'pressure')
    sim.add_controller_instrument('MyPumpStatus', 'link', '1', 'status')

This adds two ICS modules to the RealtimeSimulator, one of which is
read-only (the tank pressure) and one of which is read-write (the pump
status).

At each step in the simulation, the RealtimeSimulator will make calls
to the user's ICS ``myicslink`` to pass data back and forth and 
synchronize the simulation clocks. The ``UserICSLink`` class needs
to proivide three functions:

* a function that can receive a timestep value and a dictionary of
  ICS module names and their values; this function should then pass
  the values to the ICS 
* a function that can return a dictionary of ICS module names and the
  new values they should now be set to at the new timestep; this
  function should read values from the ICS
* a function that will return a boolean value indicating whether
  the realtime simulator has finished

For the ``UserICSLink`` example, let us define the following functions:

.. code:: python

    class UserICSLink:

        def my_wntr_to_ics_function(self, ts: int, values: dict):
            # do the communications
            pass
        
        def my_ics_to_wntr_function(self, ts: int) -> dict:
            # do the communications
            pass

        def my_ics_sync_function(self, ts: int) -> bool:
            # do the synchronization
            # return one of three values
            # # True -> stop the simulation
            # # False -> keep going
            pass


When the RealtimeSimulator is initialized, these functions will be passed
in as arguments:

.. code:: python

    sim.initialize(receive=myicslink.my_ics_to_wntr_function,
                   transmit=myicslink.my_wntr_to_ics_function,
                   stop=myicslink.my_ics_sync_function)


This is the extent of the API for the communications. Everything in the
ICS link class is defined by the user. Note that the timestep that is 
passed to the ICS link class is the number of seconds since the WNTR 
simulation start. It is up to the ICS link to convert that value to 
clocktime or the external model time.

Running the realtime simulation
-------------------------------

The ``run_sim()`` command is simpler in the ReatlimeSimulator than in 
the standard WNTR simulators since the configuration is done in the 
``initialize`` function instead. The ``run_sim`` function takes only
two arguments,

* limit (int, deafult Inf): a fallback simulation duration just to make sure the
  simulator doesn't get caught in an infinite loop. However, the 
  default value is infinity ...
* cleanup (bool, default True): indicate whether the simulation should
  close the simulation when the limit is reached or the synchronization
  function says to stop. By default, when ``run_sim`` is told to stop,
  it will set the duration to the last timestep value; if this value is
  false, it will simply end without performing cleanup actions. This 
  option is needed to handle the two methods of linking the simulators
  described below.

Running the realtime simulator starts the following loop:

.. uml::

    @startuml
    start
    ->""run_sim""(""limit"", ""cleanup"");
    repeat 
    :Read commands from the ICS by 
    calling ICS link function attached
    to ""self.receive"";
    :Run the hydaulic 
    (and water quality if EPANET) 
    simulation for one time step;
    :Send data to the ICS, by calling 
    the ICS link function attached
    to ""self.transmit"";
    :Call the synchronization function
    attached to ""self.stop"";
    repeat while (ICS Link says continue
    and ""limit"" not reached?) is (yes)
    -> no;
    if (Check ""cleanup"" value) is (True) then
        :set duration to now;
        stop
    else (False)
    stop
    @enduml



Linking the simulators
----------------------

There are two possible approaches to using the WNTR realtime simulator
in conjunction with an external simulation. One approach is to write 
a separate driver process, i.e., a ``__main__()`` function script, that
configures the ICS link and WNTR RealtimeSimulator classes and then 
runs the simulator. This process is completely separate from the other
simulator and the ICS link uses files, a database, or network communications
to interact with the other simulation. This is the most likely scenario.

The second approach is to have the other simulation create the WNTR 
realtime simulator as a persistent object and then call ``run_sim``
repeatedly as needed. In this case, the ICS link is probably going to be
reading/writing to some object in memory. The synchronization function will
need to be somewhat more involved, but an example will be presented for
this method later.



.. uml::

    @startuml
    title 
    One possible workflow for a main process
    to use WNTR with cyber or energy simulations

    end title
    |c| Communications Interface \n SCADA/Cyber Provider
    |d| Main Process
    |w| WNTR Simulator
    |d|
    start
    :Load configuration
    and network model;
    -> <code>
    config, wn
    </code>;
    fork 
    |c|
    -> <code>
    (config)
    </code>;
    :Create and configure 
    communicator;
    -> <code>
    comm
    </code>;
    fork again
    |w|
    -> <code>
    (wn)
    </code>;
    :Create simulator;  
    -> <code>
    sim
    </code>;
    |d|
    end fork
    |d|
    while (Sensors to configure?)
    -> yes
    <code>
    (config.sensor)
    </code>;
    |w|
    :Map SCADA to wn;
    endwhile
    -> no;
    |d|
    :Initialize simulator;
    -> <code>
    comm
    </code>;
    |w| 
    :Map internal simulator commands to 
    functions on communicator. E.g.:
    <code>
    sim.transmit := comm.send_scada_messages
    sim.receive := comm.get_scada_messages
    sim.stop := comm.get_term_signal
    </code>
    and then run timestep 0;
    |d|
    :Run simulation;
    -> <code>
    time_limit
    </code>;
    |w|
    repeat 
    ':Advance time;
    :Run model;
    :Read model data;
    ':Send current values;
    -> <code>
    (t, values)
    </code>;
    |c|
    :Relay sensor values to RTU<
    |w|
    :Check for new data;
    -> <code>
    (t)
    </code>;
    |c|
    :Get commands from RTU>
    -> <code>
    values
    </code>;
    |w|
    :Set new values in model;
    ':Check for terminate signal;
    -> <code>
    (t)
    </code>;
    |c|
    :Look for term signal>
    -> <code>
    signal
    </code>;
    |w|
    :Check runtime limits;
    repeat while (Terminate signal received
    or limit reached?) is (no)
    ->yes;
    |d|
    :Close simulator;
    |w|
    :Read results, close DLLs;
    -> <code>
    results
    </code>;
    |d|
    :Final output;
    stop

    @enduml
