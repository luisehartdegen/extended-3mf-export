import adsk.core
import os

import adsk.fusion
from ...lib import fusionAddInUtils as futil
from ... import config

import traceback

app = adsk.core.Application.get()
ui = app.userInterface

# TODO ********************* Change these names *********************
CMD_ID = f'{config.COMPANY_NAME}_{config.ADDIN_NAME}_mark_modifier'
CMD_NAME = 'Mark as Modifier'
CMD_Description = 'Mark the selected body as modifier for OrcaSlicer'

IS_PROMOTED = True

WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID = 'SolidScriptsAddinsPanel'
COMMAND_BESIDE_ID = 'ScriptsManagerCommand'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

BODY_SELECTION_INPUT = 'body_selection_input'
MODIFIER_TYPE_INPUT = 'modifier_type'
WALL_LOOPS_INPUT = 'wall_loops_input'

MODIFIER_SUPPORT_BLOCKER = 'Support Blocker'
MODIFIER_SUPPORT_ENHANCER ='Support Enhancer'
MODIFIER_WALL_LOOPS = 'Wall Loops'

# Local list of event handlers used to maintain a reference so
# they are not released and garbage collected.
local_handlers = []


# Executed when add-in is run.
def start():
    # Create a command Definition.
    cmd_def = ui.commandDefinitions.addButtonDefinition(CMD_ID, CMD_NAME, CMD_Description, os.path.join(SCRIPT_DIR, 'resources', ''))

    # Define an event handler for the command created event. It will be called when the button is clicked.
    futil.add_handler(cmd_def.commandCreated, command_created)

    # ******** Add a button into the UI so the user can run the command. ********
    # Get the target workspace the button will be created in.
    workspace = ui.workspaces.itemById(WORKSPACE_ID)

    # Get the panel the button will be created in.
    panel = workspace.toolbarPanels.itemById(PANEL_ID)

    # Create the button command control in the UI after the specified existing command.
    control = panel.controls.addCommand(cmd_def, COMMAND_BESIDE_ID, False)

    # Specify if the command is promoted to the main toolbar. 
    control.isPromoted = IS_PROMOTED


# Executed when add-in is stopped.
def stop():
    # Get the various UI elements for this command
    workspace = ui.workspaces.itemById(WORKSPACE_ID)
    panel = workspace.toolbarPanels.itemById(PANEL_ID)
    command_control = panel.controls.itemById(CMD_ID)
    command_definition = ui.commandDefinitions.itemById(CMD_ID)

    # Delete the button command control
    if command_control:
        command_control.deleteMe()

    # Delete the command definition
    if command_definition:
        command_definition.deleteMe()


# Function that is called when a user clicks the corresponding button in the UI.
# This defines the contents of the command dialog and connects to the command related events.
def command_created(args: adsk.core.CommandCreatedEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Created Event')

    # https://help.autodesk.com/view/fusion360/ENU/?contextId=CommandInputs
    inputs = args.command.commandInputs

    # TODO Define the dialog for your command by adding different inputs to the command.

    # Create a selection input that allows exactly one body to be selected
    selection = inputs.addSelectionInput(BODY_SELECTION_INPUT, 'Please select body', 'Select body to be marked as modifier')
    selection.addSelectionFilter("Bodies")
    
    # create dropdown menu to select wall loop / support blocker (default) / support enhancer
    dropdown = inputs.addDropDownCommandInput(MODIFIER_TYPE_INPUT, 'Modifier Type', adsk.core.DropDownStyles.TextListDropDownStyle)
    dropdown.isFullWidth = True
    dropdown.maxVisibleItems = 3
    dropdownItems = dropdown.listItems
    dropdownItems.add(MODIFIER_SUPPORT_BLOCKER, True, '')
    dropdownItems.add(MODIFIER_SUPPORT_ENHANCER, False, '')
    dropdownItems.add(MODIFIER_WALL_LOOPS, False, '')    

    # Create a value input field to set amount of wall loops if that option is selected
    wall_loop_input = inputs.addValueInput(WALL_LOOPS_INPUT, 'Amount of Wall Loops', '', adsk.core.ValueInput.createByString('2'))
    wall_loop_input.isVisible = False
    wall_loop_input.minimumValue = 1

    # TODO Connect to the events that are needed by this command.
    futil.add_handler(args.command.execute, command_execute, local_handlers=local_handlers)
    futil.add_handler(args.command.inputChanged, command_input_changed, local_handlers=local_handlers)
    futil.add_handler(args.command.executePreview, command_preview, local_handlers=local_handlers)
    futil.add_handler(args.command.validateInputs, command_validate_input, local_handlers=local_handlers)
    futil.add_handler(args.command.destroy, command_destroy, local_handlers=local_handlers)


# This event handler is called when the user clicks the OK button in the command dialog or 
# is immediately called after the created event not command inputs were created for the dialog.
def command_execute(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Execute Event')

    # TODO ******************************** Your code here ********************************

    # Get a reference to your command's inputs.
    inputs = args.command.commandInputs

    try:
        selection_command_input: adsk.core.SelectionCommandInput = inputs.itemById(BODY_SELECTION_INPUT)
        dropdown_command_input: adsk.core.DropDownCommandInput = inputs.itemById(MODIFIER_TYPE_INPUT)
        selected_modifier = dropdown_command_input.selectedItem.name

        active_selection: adsk.fusion.BRepBody = selection_command_input.selection(0).entity

        design:adsk.fusion.Design = adsk.fusion.Design.cast(app.activeProduct)

        rootComp = design.rootComponent
        features = rootComp.features

        materialLibs = app.materialLibraries

        matLib = None
        for i in range(materialLibs.count):
            lib = materialLibs.item(i)
            if lib.name == 'Extended3mfExport':
                matLib = lib
                break

        # Load only if not already loaded
        if not matLib:
            matLib = materialLibs.load(os.path.join(SCRIPT_DIR, 'resources', 'Extended3mfExport.adsklib'))

        if selected_modifier == MODIFIER_SUPPORT_BLOCKER:
            appear_lib = matLib.appearances.item(0)
        elif selected_modifier == MODIFIER_SUPPORT_ENHANCER:
            appear_lib = matLib.appearances.item(1)
        elif selected_modifier == MODIFIER_WALL_LOOPS:
            wall_loops_input: adsk.core.ValueCommandInput = inputs.itemById(WALL_LOOPS_INPUT)
            appear_lib = matLib.appearances.item(2)

        appear_copy = get_or_add_appearance(design, appear_lib)
        active_selection.appearance = appear_copy

        # unload library 
        if matLib.isNative == False:
            matLib.unload()  

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

# This event handler is called when the command needs to compute a new preview in the graphics window.
def command_preview(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Preview Event')
    inputs = args.command.commandInputs


# This event handler is called when the user changes anything in the command dialog
# allowing you to modify values of other inputs based on that change.
def command_input_changed(args: adsk.core.InputChangedEventArgs):
    changed_input = args.input

    # General logging for debug.
    futil.log(f'{CMD_NAME} Input Changed Event fired from a change to {changed_input.id}')

    if changed_input.id == MODIFIER_TYPE_INPUT:
        if adsk.core.DropDownCommandInput.cast(changed_input).selectedItem.name == MODIFIER_WALL_LOOPS:
            args.inputs.itemById(WALL_LOOPS_INPUT).isVisible = True
        else:
            args.inputs.itemById(WALL_LOOPS_INPUT).isVisible = False


# This event handler is called when the user interacts with any of the inputs in the dialog
# which allows you to verify that all of the inputs are valid and enables the OK button.
def command_validate_input(args: adsk.core.ValidateInputsEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Validate Input Event')

    inputs = args.inputs
    
    # Verify the validity of the input values. This controls if the OK button is enabled or not.
    selectionInput = inputs.itemById(BODY_SELECTION_INPUT)
    dropdownInput = inputs.itemById(MODIFIER_TYPE_INPUT)

    if selectionInput and dropdownInput.selectedItem: 
        True
    else: 
        False


# This event handler is called when the command terminates.
def command_destroy(args: adsk.core.CommandEventArgs):
    # General logging for debug.
    futil.log(f'{CMD_NAME} Command Destroy Event')

    global local_handlers
    local_handlers = []


def get_or_add_appearance(des: adsk.fusion.Design, lib_appearance: adsk.core.Appearance):
    existing = des.appearances.itemByName(f"{lib_appearance.name}_Copied")
    if existing:
        return existing
    else:
        return des.appearances.addByCopy(lib_appearance, f"{lib_appearance.name}_Copied")
