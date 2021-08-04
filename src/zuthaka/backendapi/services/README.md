# Service layer
This module should be in charge of handle every instance of C2 to respect our patterns of consistency vs availability. It should create an event of an interaction made by the user and stored it in a queue to be consumed by the C2s

**consistency vs availability** every resource that is being created, updated or deleted should prefer consistency over availability. In the other hand every list of elements and types in the system should prefer availability, but still perform some kind of consistency work. 


## Abstract Class for C2 handling

The class used for handling an specific C2, should heredate from C2Type and implement functions to manage Zuthaka's resources (this might be referred as a type of integration). 

**API resources** 
* C2
* Listeners
* Launchers
* Agents

### Functions to implement 
#### C2
* heartbeat
#### listeners
* list listeners
* create listener. (type?)
* update listener. (type?)
* delete listener
* detail listener
#### launchers
* list launchers. (if not possible, we should handle it from the service layer and return the ones tored in DB)
* create launcher
* retrive launcher
#### agent
* interact
