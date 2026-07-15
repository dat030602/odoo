/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";

import fieldRegistry from "web.field_registry";
const { Component, useState, useRef, onMounted, onWillUpdateProps, onWillStart } = owl;

jQuery.expr[':'].caseContains = function(a, i, m) {
    return jQuery(a).text().toUpperCase()
     .indexOf(m[3].toUpperCase()) >= 0;
};

export class kpiFormulaWidget extends Component {
    async setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.record = this.props.record
        this.KpiMeasures = useRef('MEASURE')
        this.action = useService("action");
        this.KpiKPI = useRef('KPI')
        this.KpiConst = useRef('CONST')
        this.formulaRef = useRef('formulaRef')

        this.constants = {};
        this.formulaparts = {};
        this.operands = {};
        this.measures = {};
        this.kpis = {};
        console.log("this", this)
        onWillStart(this.willStart);
        onMounted(this.onMounted)
    }
    async willStart(){
        await loadBundle({
            jsLibs: [
                '/biz_kpi_scorecard/static/lib/draggabilly/draggabilly.pkgd.js',
            ],
        });
        var self = this
        var kpiID = parseInt(self.record.data.id);
        const result = await this.rpc("/web/dataset/call_kw/kpi.item/action_return_measures", {
            model: 'kpi.item',
            method: 'action_return_measures',
            args: [[kpiID], self.props.value],
            kwargs: {}
        })
        this.constants = result.constants;
        this.formulaparts = result.formulaparts;
        this.operands = result.operands;
        this.measures = result.measures;
        this.kpis = result.kpis;
    }
    onMounted(){
        var self = this;
        self._onActivateDraggable(this.formulaRef.el.querySelectorAll('.kpi-element'));
        self._onActivateDraggable(this.formulaRef.el.querySelectorAll('.kpi-formula-part'));
    }
    _onActivateDraggable(dragEl) {
        var self = this;
        var dragEl = $(dragEl)
        var $draggable = dragEl.draggabilly({}); 
        $draggable.on( 'dragStart', function(event, pointer) {
            self._onDragStart(event, pointer);
        });
        $draggable.on( 'dragMove', function(event, pointer, moveVector) {
            self._onDragMove(event, pointer, moveVector);
        });
        $draggable.on( 'dragEnd', function(event, pointer) {
            self._onDragEnd(event, pointer);
        });
        $draggable.on( 'staticClick', function(event, pointer) {
            self._onStatiClick(event, pointer);
        });
    }
    _onDragStart (event, pointer) {
        if (!this.targetObject) {
            this.targetDOM = event.currentTarget;
            this.targetObject =  $(event.currentTarget);
            this.targetID = event.currentTarget.id;
            this.targetName = event.currentTarget.innerHTML;
            if ($(event.currentTarget).hasClass("kpi-number")) {
                this.targetName = event.currentTarget.id;
            };
            var initalOffset = this.targetObject.offset();
            this.targetObject.attr("style", "position: absolute;");
            this.targetObject.offset(initalOffset);
        };
    }
    _onDragMove (event, pointer, moveVector) {
        var self = this;        
        var targetPositions = self._calculateTargetPosition(this.targetObject); 
        if (targetPositions.containerPosition == "formula") {
            self._findClosestNeighbour(targetPositions.currentTop, targetPositions.currentLeft).then(function (neighbourData) {
                self._createFormulaPart(neighbourData.targetNeighbour, neighbourData.targetPosition);    
            })   
        }
        else {
            self._clearFormulaPart();
        };
    }
    _onDragEnd (event, pointer) {
        var self = this;
        if (self.tempPart) {
            $(self.tempPart).removeClass("temp-kpi-formula-part");
            self._onActivateDraggable($(self.tempPart));
            self.tempPart = false;    
        };
        if (self.targetObject.hasClass("kpi-element")) {
            self.targetObject.removeClass();
            self.targetObject.attr("style", "");
            self.targetObject.addClass("kpi-element");                                    
        }
        else {
            self.targetObject.remove();
        };
        self.targetObject = false;
        self.targetID = false;
        self.targetName = false;
        self.targetDOM = false;
        // notify changes
        self._renderFormula().then(function (formula) {
            self.props.record.update({
                formula: formula
            });
        });
    }
    async _onStatiClick(event, pointer) {
        // 
        var self = this;
        const action = await this.rpc("/web/dataset/call_kw/kpi.item/action_open_formula_part", {
            model: 'kpi.item',
            method: 'action_open_formula_part',
            args: [event.currentTarget.id],
            kwargs: {}
        })

        if (action) {
            this.action.doAction(action);
        }
    }
    _renderFormula() {
        var self = this,
            allParts = $(this.formulaRef.el).find(".kpi-formula-part").not(".temp-kpi-formula-part"),

            doneFormula = $.Deferred();
        var allCounter = allParts.length;
        if (allCounter > 0) {
            var formula = ""
            _.each(allParts, async function (part) {
                allCounter --;
                if (allCounter == 0) {
                    if (part && part.id) {
                        formula += part.id;
                    };
                    doneFormula.resolve(formula)
                }
                else {
                    if (part && part.id) {
                        formula += part.id + ";";
                    };  
                };
            });
        }
        else {
            doneFormula.resolve("");
        };
        return doneFormula;
    }
    _calculateContainerGrid(container_selector) {
        var formulaContainer = $(this.formulaRef.el).find(container_selector);
        var formulaContainerOffset = formulaContainer.offset();
        return {
            "y1": formulaContainerOffset.top,
            "y2": formulaContainerOffset.top + formulaContainer.outerHeight(),
            "x1": formulaContainerOffset.left,
            "x2": formulaContainerOffset.left + formulaContainer.outerWidth(),
        };
    }
    _calculateTargetPosition(targetObject) {
        var position = targetObject.offset();
        var currentTop = position.top, 
            currentLeft = position.left,
            formulaGrid = this._calculateContainerGrid(".kpi-content"),
            containerPosition = false;
        if (currentTop >= formulaGrid.y1 && currentTop <= formulaGrid.y2 
            && currentLeft + targetObject.outerWidth() >= formulaGrid.x1 && currentLeft <= formulaGrid.x2) {
            // inside formula container
            containerPosition = "formula"
        };
        return {
            "currentTop": currentTop,
            "currentLeft": currentLeft,
            "containerPosition": containerPosition,
        };
    }
    _findClosestNeighbour(currentTop, currentLeft) {
        var self = this,
            allParts = $(this.formulaRef.el).find(".kpi-formula-part").not(".temp-kpi-formula-part"),
            doneNighbour = false;
        var allCounter = allParts.length,
            targetAn = false,
            closestDistance = false,
            targetPosition = false; 
        if (allCounter > 0) {
            _.each(allParts, async function (part) {
                if (part != self.targetDOM) {
                    var offset = $(part).offset();
                    var partTop = offset.top, 
                        partLeft = offset.left;
                    var xDist = partTop - currentTop,
                        yDist = partLeft - currentLeft;
                    var distance = Math.sqrt(xDist * xDist + yDist * yDist);
                    if (!closestDistance || distance < closestDistance) {
                        targetAn = $(part);
                        closestDistance = distance;
                        //  && currentTop <= partTop + $(part).outerHeight()
                        if (currentLeft <= partLeft + 2) {
                            targetPosition = "left";
                        }
                        else {
                            targetPosition = "right";
                        };
                    };
                };

                allCounter --;
                if (allCounter == 0) {
                    doneNighbour = {
                        "targetNeighbour": targetAn, 
                        "targetPosition": targetPosition,
                    }
                };
            });
        }
        else {
            // if not formula part yet
            doneNighbour = {
                "targetNeighbour": $(this.formulaRef.el).find(".kpi-formula-parts"),
                "targetPosition": "inside",
            }
        };
        return Promise.resolve(doneNighbour);
    }
    _clearFormulaPart() {
        if (this.tempPart) {
            this.tempPart.remove();    
        };   
    }
    _createFormulaPart(targetNeighbour, targetPosition) {
        if (this.tempPart) {
            this.tempPart.remove();    
        };
        if (this.targetID && this.targetName && targetPosition 
            && (targetNeighbour.hasClass("kpi-formula-part") || targetNeighbour.hasClass("kpi-formula-parts")) )
        {
            this.tempPart = document.createElement("div");
            this.tempPart.setAttribute("id", this.targetID);
            this.tempPart.innerHTML = this.targetName;
            $(this.tempPart).addClass("kpi-formula-part");
            $(this.tempPart).addClass("temp-kpi-formula-part");           
            if (targetPosition == "left") {
                targetNeighbour.before(this.tempPart);
            }
            else if (targetPosition == "right"){
                targetNeighbour.after(this.tempPart);
            }
            else {
                $(this.tempPart).appendTo(targetNeighbour);
            };
        };
    }
    _onChangeNumber(event){
        var parentElem = $(event.currentTarget).parent();
        parentElem[0].setAttribute("id", event.currentTarget.value);
    }
    _onSearch(event) {
        var searchValue = event.currentTarget.value,
            setId = event.currentTarget.id;

        if (setId) {
            var setContainer = false;
            if (setId == "MEASURE") {
                setContainer = this.KpiMeasures
            } else if (setId == "KPI") {
                setContainer = this.KpiKPI;
            } else if (setId == "CONST") {
                setContainer = this.KpiConst
            };
            if (setContainer) {
                var allVariables = $(setContainer.el).find(".kpi-variable");
                if (searchValue) {
                    allVariables.addClass("kpi-hidden");
                    var searchMatches = $(setContainer.el).find(".kpi-variable:caseContains("+ searchValue +")");
                    searchMatches.removeClass("kpi-hidden");
                } 
                else {
                    allVariables.removeClass("kpi-hidden");
                }
            };
        };           
    }
 
};
kpiFormulaWidget.template = "biz_kpi_scorecard.formulaWidgetTemplate";
kpiFormulaWidget.supportedTypes = ["char"];
registry.category("fields").add("kpiFormulaWidget", kpiFormulaWidget);
