#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 27 10:58:06 2024

@author: fabian
"""

from pyomo.environ import *

model = AbstractModel()

#nodes in network
model.N = Set()
#arcs in network
model.A = Set(within=model.N*model.N)

#source
model.s = Param(within=model.N)
#sing
model.t = Param(within=model.N)
#flow capacity limits
model.c = Param(model.A)

#flow over each arc
model.f = Var(model.A, within=NonNegativeReals)#NonNegativeIntegers)
#binary variable to toggle flow
model.y = Var(model.A, domain=Binary, initialize=0)



#Maximizie the flow into the sink nodes
def total_rule(model):
    return sum(model.f[i,j] for (i,j) in model.A if j==value(model.t))
model.total = Objective(rule=total_rule, sense=maximize)

#limit rule only necessary for links where 0/max_flow rule does not apply
def limit_rule(model, i, j):
        if (i == value(model.s)) or (i == value(model.t)) or (j == value(model.s)) or (j == value(model.t)):
            return model.f[i, j] <= model.c[i, j]
        else: 
            return Constraint.Skip
model.limit = Constraint(model.A, rule=limit_rule)

#additionalrule where flow is either zero or max capacity
def new_rule(model, i, j):
    #if (i == value(model.s)) or (i == value(model.t)) or (j == value(model.s)) or (j == value(model.t)): this worked alright
    if (i == value(model.s)) or (i == value(model.t)) or (j == value(model.s)):   
        return Constraint.Skip
    #return ((model.f[i,j] == (model.c[i,j]) or model.f[i,j] == 0))
    return model.f[i,j] == model.c[i,j] * model.y[i,j]
model.new = Constraint(model.A, rule=new_rule)


# Enforce flow through each node
def flow_rule(model, k):
    if k == value(model.s) or k == value(model.t):
        return Constraint.Skip
    inFlow  = sum(model.f[i,j] for (i,j) in model.A if j == k)
    outFlow = sum(model.f[i,j] for (i,j) in model.A if i == k)
    return inFlow == outFlow
model.flow = Constraint(model.N, rule=flow_rule)






model.flow = Constraint(model.N, rule=flow_rule)

#%%needed for use in in-python scripts


def create_model():
    model = AbstractModel()

    # Nodes in network
    model.N = Set()
    # Arcs in network
    model.A = Set(within=model.N * model.N)

    # Source
    model.s = Param(within=model.N)
    # Sink
    model.t = Param(within=model.N)
    # Flow capacity limits
    model.c = Param(model.A)

    # Flow over each arc
    model.f = Var(model.A, within=NonNegativeReals)  # Or NonNegativeIntegers
    # Binary variable to toggle flow
    model.y = Var(model.A, domain=Binary, initialize=0)

    # Maximize the flow into the sink nodes
    def total_rule(model):
        return sum(model.f[i, j] for (i, j) in model.A if j == value(model.t))
    model.total = Objective(rule=total_rule, sense=maximize)

    #limit rule only necessary for links where 0/max_flow rule does not apply
    def limit_rule(model, i, j):
        if (i == value(model.s)) or (i == value(model.t)) or (j == value(model.s)) or (j == value(model.t)):
            return model.f[i, j] <= model.c[i, j]
        else: 
            return Constraint.Skip
    model.limit = Constraint(model.A, rule=limit_rule)

    # Additional rule where flow is either zero or max capacity
    def new_rule(model, i, j):
        if (i == value(model.s)) or (i == value(model.t)) or (j == value(model.s)) or (j == value(model.t)):
            return Constraint.Skip
        return model.f[i, j] == model.c[i, j] * model.y[i, j]
    model.new = Constraint(model.A, rule=new_rule)

    # Enforce flow through each node
    def flow_rule(model, k):
        if k == value(model.s) or k == value(model.t):
            return Constraint.Skip
        inFlow = sum(model.f[i, j] for (i, j) in model.A if j == k)
        outFlow = sum(model.f[i, j] for (i, j) in model.A if i == k)
        return inFlow == outFlow
    model.flow = Constraint(model.N, rule=flow_rule)

    return model
