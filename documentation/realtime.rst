.. raw:: latex

    \clearpage

.. _realtime_simulation:

Real-time simulation
===============================

Real-time simulations are intended for use with external simulation
software, such as cyber security simulations or linked energy/water
simulations. In these scenarios, WNTR is being used to provide the 
"ground truth" for the physical system state. In other words, WNTR
is being modified by external commands, not by the typical internal
rules or controls that are included in the WaterNetworkModel.

One item to note is that "real-time" does not necessarily require the
model to be run at wall-clock rate. It merely indicates that WNTR is
running each hydraulic step with a call to an external function to
determine when to proceed, which allows this external function to 
synchronize WNTR's simulation clock with a different simulation's 
clock.

The main issue to consider in the real-time paradigm is that most of
the work is "someone else's problem"; i.e., WNTR does not provide 
a class that will communicate with a simulated industrial control
system, the user must code that piece themselves. Likewise, in the
case of a cyber attack siimulation, WNTR is *not* the piece that is 
being attacked. All WNTR does is provide the "real world" state of 
the WDS.

Take the following example - as part of a cyber attack simulation, 
a researcher wants to use WNTR as the hydraulic simulator. Using the
real-time WNTR module, the researcher can write a class that will 
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

WNTR real-time API
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
    sim = EpanetSimulator_RT(wn)
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
  the real-time simulator has finished

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

Running the real-time simulation
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

Running the real-time simulator starts the following loop:

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

There are two possible approaches to using the WNTR real-time simulator
in conjunction with an external simulation. One approach is to write 
a separate driver process, i.e., a ``__main__()`` function script, that
configures the ICS link and WNTR RealtimeSimulator classes and then 
runs the simulator. This process is completely separate from the other
simulator and the ICS link uses files, a database, or network communications
to interact with the other simulation. This is the most likely scenario.

The second approach is to have the other simulation create the WNTR 
real-time simulator as a persistent object and then call ``run_sim``
repeatedly as needed. In this case, the ICS link is probably going to be
reading/writing to some object in memory. The synchronization function will
need to be somewhat more involved, but an example will be presented for
this method later.



.. uml::

    @startuml
    title 
    Example real-time workflow with a custom driver script

    end title
    |c| User's ICS-WNTR link class
    |d| User's custom driver script
    |w| WNTR RealtimeSimulator class
    |d|
    start
    :Load configuration, ""config""
    and WDS network model, ""wn"";
    :Delete any rules or controls in the 
    ""wn"" model so that all control is 
    external.;
    :Create link object ""myicslink"";
    |c|
    :""_init_(*args, **kwargs)"";
    |d|
    :Create WNTR simulator, ""sim"";
    |w|
    :""_init_(wn, **kwargs)"";
    |d|
    while (sensors to configure?) is (yes)
    :call ""sim.add_sensor_instrument(**kwargs)""
    or ""sim.add_controller_instrument(**kwargs)"";
    |w|
    :maps ICS entries to ""wn"" model elements;
    endwhile
    ->no;
    |d|
    :Initialize simulator
    ""sim.initialize(**kwargs)"";
    |w| 
    :Maps internal simulator commands to 
    functions on communicator. E.g.:
    ""self.transmit = myicslink.some_function_1""
    ""self.receive = myicslink.f2""
    ""self.stop = some_other_function"";
    :run hydraulic timestep for ""ts = 0"";
    |d|
    :Run WNTR simulation
    ""sim.run_sim(limit=?, cleanup=True)"";
    |w|
    repeat 
    :Ask ISC link for new data
    ""ics_values = self.receive(ts)"";
    -> pass sim time as an integer;
    |c|
    :Get commands from ICS; e.g.,
    from network traffic messages or
    from some user-coded control rules>
    -> return values in a dictionary;
    |w|
    :Set new statuses in simulator
    ""self._set_sensor_values(ics_values)"";
    :Run one simulation timestep and
    calculate new hydraulic/water quality
    values for the simulation, 
    advance timestep ""ts"";
    :Get the data from the new simulation state 
    ""new_values = self._get_sensor_values()"";
    :Send the data to the ICS link
    ""self.transmit(ts, new_values)"";
    -> pass values in a dictionary;
    |c|
    :Relay sensor values to ICS; e.g.,
    as network messages or
    by writing to a database or file<
    -> no return value;
    |w|
    :Check for terminate signal
    ""done = self.stop(ts)"";
    -> pass sim time as integer;
    |c|
    :Execute user's custom code to do clock 
    synchronization and/or look for a 
    termination/kill signal from the 
    outside ICS simulator.
    return ""True"" if it is time to stop>
    -> return a boolean;
    |w|
    :Check runtime limits;
    repeat while (""ts < limit and not done""?) is (yes)
    ->no;
    if (cleanup?) is (always yes for this example) then
    :end simulation completely;
    else 
    -[hidden]->
    endif
    |d|
    :Close simulator
    ""results = sim.close()"";
    |w|
    :Close all DLLs, write report;
    :Create a WNTR results object
    and return it to the user's driver;
    -> return ""wntr.sim.Results"" object;
    |d|
    :Do custom postprocessing as 
    written by the user;
    stop

    @enduml
