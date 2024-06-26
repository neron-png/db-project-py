import copy
from pprint import pprint
from Record import Record
from RTReeUtil import rectangleContains, overlap, rectAddPoint, min_i, rectangleArea
import RTReeUtil
import config
from RTReeInsert.ChooseSubtree import chooseSubtreeLeaf, flatten, chooseSubtree
from RTReeInsert.FindSplit import findSplit
from random import randint
import StorageHandler

def insertData(nodeCap: int, m: int, nodes: dict, record: Record) -> dict: 
    """
    :param Record dict: {
                        "name": str,
                        "coords": list [x, y, z...]
                        }
    :return: Nodes
    """

    """ 1. Insert the data to the datafile to retrieve the bID and sID """
    """ Create entry as such: {
                        "bID": int,
                        "sID": int,
                        "coords": list [x, y, z...]
                        }"""
    
    # pprint(nodes[0]["records"])
    
    if nodes["root"]["first_insert"]:
            nodes["root"]["first_insert"] = False
            nodes[nodes["root"]["id"]] = {"id": 0, "type": "l", "level": 0, "records": [], "rectangle": [[0, 0], [1, 1]]}
    
    entry = {"coords": record.coords, "bID": StorageHandler.writeRecordToDisk(record), "sID": record.id} # TODO revert this!
    # entry = {"coords": record.coords, "bID": 666, "sID": record.id} 
    return insert(nodeCap=nodeCap, m=m, nodes=nodes, entry=entry, level=0)

    

def insert(nodeCap: int, m: int, nodes: dict, entry: dict, level: int) -> dict:
    """
    :return: Nodes
    """
    # print(level, entry)
    
    # Check if we have a new root
    # if level > nodes["root"]:
    #     pass
    """ I1: Invoke chooseSubtree to find the subtree """
    if "coords" in entry.keys():
        subtree = chooseSubtreeLeaf(nodes, entry["coords"])
    else:
        subtree = chooseSubtree(nodes=nodes, level=level, rect=entry["rectangle"])
    subtree = flatten(subtree)
    # print(subtree[-1])

    # pprint(findSplit(nodeCap=nodeCap, m=m, nodes=nodes, splitNodeID=subtree[-2]))
    
    """ I2: Accomodate Entry in N, check if overflown and call treatment """
    overFlowFlag = False
    if nodes[subtree[-1]]["type"] == "l" and "coords" in entry.keys():
        nodes[subtree[-1]]["records"].append(entry)
        nodes[subtree[-1]]["rectangle"] = RTReeUtil.leafBoundingRect([item["coords"] for item in nodes[subtree[-1]]["records"]])
        if len(nodes[subtree[-1]]["records"]) > nodeCap:
            overFlowFlag = True
    else:
        nodes[subtree[-1]]["children"].append(entry["id"])
        nodes[entry["id"]] = entry
        nodes[subtree[-1]]["rectangle"] = RTReeUtil.rectBoundingBox([nodes[ID]["rectangle"] for ID in nodes[subtree[-1]]["children"]])
        if len(nodes[subtree[-1]]["children"]) > nodeCap:
            overFlowFlag = True
    if overFlowFlag:
        overflowTreatment(nodes=nodes, nodeCap=nodeCap, level=level, m=m, overflownID=subtree[-1])


    return nodes


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


def overflowTreatment(nodes: dict, nodeCap: int, level: int, m:int, overflownID: int):
    
    """ OT1: if level is not the root level and this is the first Overflow Treatment for this level """
    if config.OVERFLOWTREATMENT[level] == 0 and not nodes[nodes["root"]["id"]]["level"] == level:
        REINSERT_P = int(nodeCap*config.SPLIT_P)
        REINSERT_P = REINSERT_P if nodeCap + 1 - REINSERT_P >= m else nodeCap - m
        config.OVERFLOWTREATMENT[level] += 1
        #Check if the node is a leaf node or not
        if nodes[overflownID]["type"] == "l":
            
            """ RI1/2 For all M+1 sort based on descending distance to center of parent rectangle """
            # pprint(nodes[overflownID])
            nodes[overflownID]["records"] = sorted(nodes[overflownID]["records"], key=lambda point: RTReeUtil.calcPointToRect(point["coords"], nodes[overflownID]["rectangle"]), reverse=True)  
            # pprint(nodes[overflownID])
            """ RI3 Remove the first p entries from the parent and readjust rectangle """
            
            removed_entries = copy.deepcopy(nodes[overflownID]["records"][:REINSERT_P])
            del nodes[overflownID]["records"][:REINSERT_P]
            nodes[overflownID]["rectangle"] = RTReeUtil.leafBoundingRect([item["coords"] for item in nodes[overflownID]["records"]])
            
            """ RI4 Close reinsert the removed entries """
            # Changing the sort in removed entries to ascending
            removed_entries.reverse()
            for entry in removed_entries:
                insert(nodeCap= nodeCap, m= m, nodes= nodes, entry= entry, level= 0)
            
        else:
            """ RI1/2 For all M+1 sort based on descending distance to center of parent rectangle """
            nodes[overflownID]["children"] = sorted(nodes[overflownID]["children"], key=lambda childID: RTReeUtil.calcRectToRect(nodes[childID]["rectangle"], nodes[overflownID]["rectangle"]), reverse=True)  

            """ RI3 Remove the first p entries from the parent and readjust rectangle """
            removed_entries = copy.deepcopy(nodes[overflownID]["children"][:REINSERT_P])
            del nodes[overflownID]["children"][:REINSERT_P]
            nodes[overflownID]["rectangle"] = RTReeUtil.rectBoundingBox([nodes[childID]["rectangle"] for childID in nodes[overflownID]["children"]])
            
            """ RI4 Close reinsert the removed entries """
            # Changing the sort in removed entries to ascending
            removed_entries.reverse()
            for entryID in removed_entries:
                insert(nodeCap= nodeCap, m= m, nodes= nodes, entry= nodes[entryID], level= level)
        pass
    else:
        """ SPLIT """
        split_groups = findSplit(nodeCap=nodeCap, m=m, nodes=nodes, splitNodeID=overflownID)
        
        # Check if we have entries, leaf nodes or nodes
        """ I3: If overflow treatment was called and there was a split, propagate upwards """
        if "id" not in split_groups[0][0].keys():
            # We have entries
            nodes[overflownID]["records"] = copy.deepcopy(split_groups[0])
            nodes[overflownID]["rectangle"] = RTReeUtil.leafBoundingRect([item["coords"] for item in nodes[overflownID]["records"]])

            # Adding a new node to house the split items
            # Finding the maximum ID in the tree
            keys = [int(key) if isinstance(key, int) else 0 for key in list(nodes.keys())] #NOTE: This includes the "root" key
            max_existing_id = max(keys)
            new_id = max_existing_id+1
            
            newNode = copy.deepcopy(nodes[overflownID])
            newNode["records"] = copy.deepcopy(split_groups[1])
            newNode["id"] = new_id
            newNode["rectangle"] = RTReeUtil.leafBoundingRect([item["coords"] for item in newNode["records"]])
            
            # Propagate change upwards
            # Checking if it's a root split
            if newNode["level"] == nodes["root"]["level"]:
                # If so, let's create a new root
                nodes[newNode["id"]] = copy.deepcopy(newNode)
                
                new_root_id = RTReeUtil.generateKey(nodes)
                nodes["root"]["id"] = new_root_id
                nodes["root"]["level"] = newNode["level"]+1
                
                nodes[new_root_id] = copy.deepcopy(newNode)
                nodes[new_root_id]["id"] = new_root_id
                nodes[new_root_id]["children"] = [new_id, overflownID]
                nodes[new_root_id]["level"] = nodes["root"]["level"]
                nodes[new_root_id]["type"] = "n"
                nodes[new_root_id]["rectangle"] = RTReeUtil.rectBoundingBox(rectangles=[nodes[itemID]["rectangle"] for itemID in nodes[new_root_id]["children"]])
                del nodes[new_root_id]["records"]
            else:
                # Propagate change upwards
                insert(nodeCap= nodeCap, m= m, nodes= nodes, entry= newNode, level= newNode["level"]+1)
        else:
            
            nodes[overflownID]["children"] = copy.deepcopy([item["id"] for item in split_groups[0]])
            nodes[overflownID]["rectangle"] = RTReeUtil.rectBoundingBox(rectangles=[nodes[itemID]["rectangle"] for itemID in nodes[overflownID]["children"]])
            
            new_id = RTReeUtil.generateKey(nodes)
            
            newNode = copy.deepcopy(nodes[overflownID])
            newNode["children"] = copy.deepcopy([item["id"] for item in split_groups[0]])
            newNode["id"] = new_id
            newNode["rectangle"] = RTReeUtil.rectBoundingBox(rectangles=[nodes[itemID]["rectangle"] for itemID in newNode["children"]])

            # Checking if it's a root split
            if newNode["level"] == nodes["root"]["level"]:
                # If so, let's create a new root
                nodes[newNode["id"]] = copy.deepcopy(newNode)
                
                new_root_id = RTReeUtil.generateKey(nodes)
                nodes["root"]["id"] = new_root_id
                nodes["root"]["level"] = newNode["level"]+1
                
                nodes[new_root_id] = copy.deepcopy(newNode)
                nodes[new_root_id]["id"] = new_root_id
                nodes[new_root_id]["children"] = [new_id, overflownID]
                nodes[new_root_id]["level"] = nodes["root"]["level"]
                nodes[new_root_id]["rectangle"] = RTReeUtil.rectBoundingBox(rectangles=[nodes[itemID]["rectangle"] for itemID in nodes[new_root_id]["children"]])
                
            else:
                # Propagate change upwards
                insert(nodeCap= nodeCap, m= m, nodes= nodes, entry= newNode, level= newNode["level"]+1)

        


def reinsert():
    pass