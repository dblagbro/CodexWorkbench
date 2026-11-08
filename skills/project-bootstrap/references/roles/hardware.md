# Hardware controls

Establish exact device/target, observable state, units, operating limits, permitted actions, interlocks, stop conditions and a safe recovery method before physical actuation. Unknown limits permit read-only discovery, simulation or a disconnected fixture, not a guessed actuator command.

Treat model/provider or ownership changes as a need to reverify live device state. Never replay an interrupted hardware step from a transcript or checkpoint without checking its actual effect. Keep emergency stop and essential recovery executable without the model, coordinator or network connection that may fail. Record measured evidence and remaining limits without exposing device credentials.
