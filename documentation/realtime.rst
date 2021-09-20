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
