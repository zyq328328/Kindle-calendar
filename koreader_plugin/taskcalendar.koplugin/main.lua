--[[--
Kindle Task Calendar Plugin for KOReader

家长下达任务 -> 孩子在Kindle上点击完成 -> 反馈

@module koplugin.taskcalendar
--]]

local Dispatcher = require("dispatcher")
local InfoMessage = require("ui/widget/infomessage")
local UIManager = require("ui/uimanager")
local WidgetContainer = require("ui/widget/container/widgetcontainer")
local TextWidget = require("ui/widget/textwidget")
local ConfirmBox = require("ui/widget/confirmbox")
local _ = require("gettext")

local TaskCalendar = WidgetContainer:extend{
    name = "taskcalendar",
    is_doc_only = false,
}

-- 服务端地址
local SERVER_URL = "http://192.168.10.7:8082"

function TaskCalendar:onDispatcherRegisterActions()
    Dispatcher:registerAction("taskcalendar_action", {
        category="none",
        event="TaskCalendar",
        title=_("任务日历"),
        desc=_("查看并完成任务"),
        general=true,
    })
end

function TaskCalendar:init()
    self.ui.menu:registerToMainMenu(self)
end

function TaskCalendar:addToMainMenu(menu_items)
    menu_items.task_calendar = {
        text = _("📋 任务日历"),
        sorting_hint = "more_tools",
        callback = function()
            self:showTaskList()
        end,
    }
end

-- 显示任务列表
function TaskCalendar:showTaskList()
    local tasks = self:fetchTasks()

    if not tasks or #tasks == 0 then
        UIManager:show(InfoMessage:new{
            text = _("暂无任务"),
        })
        return
    end

    local task_dialog = self:createTaskDialog(tasks)
    UIManager:show(task_dialog)
end

-- 从服务端获取任务
function TaskCalendar:fetchTasks()
    local socket = require("socket")
    local http = require("socket.http")
    local ltn12 = require("ltn12")
    local json = require("json")

    local response = {}
    local url = SERVER_URL .. "/api/events"

    local resp, code, headers, status = http.request{
        url = url,
        method = "GET",
        sink = ltn12.sink.table(response),
    }

    if code == 200 then
        local ok, result = pcall(json.decode, table.concat(response))
        if ok then
            -- Filter pending tasks
            local pending = {}
            for _, task in ipairs(result) do
                if not task.completed then
                    table.insert(pending, task)
                end
            end
            return pending
        end
    end
    return {}
end

-- 完成任务
function TaskCalendar:completeTask(task_id)
    local socket = require("socket")
    local http = require("socket.http")
    local ltn12 = require("ltn12")

    local url = SERVER_URL .. "/api/events/" .. task_id
    local response = {}

    local resp, code = http.request{
        url = url,
        method = "PUT",
        headers = {
            ["Content-Type"] = "application/json",
        },
        source = ltn12.source.string('{"completed":true}'),
        sink = ltn12.sink.table(response),
    }

    return code == 200
end

-- 创建任务对话框
function TaskCalendar:createTaskDialog(tasks)
    local CenterContainer = require("ui/widget/container/centercontainer")
    local FrameContainer = require("ui/widget/framecontainer")

    local dialog = CenterContainer:new{}

    local content = FrameContainer:new{
        width = math.floor(Screen:getWidth() * 0.9),
        height = math.floor(Screen:getHeight() * 0.8),
    }

    -- Header
    local header = TextWidget:new{
        text = "📋 任务列表",
        face = Font:getFace("cfont", 28),
        color = 0, 0, 0,
        x = 20, y = 20,
    }
    content:addWidget(header)

    -- Task items
    local y = 80
    for i, task in ipairs(tasks) do
        if y < Screen:getHeight() - 150 then
            local task_item = self:createTaskItem(task, y)
            content:addWidget(task_item)
            y = y + 80
        end
    end

    dialog:addWidget(content)
    return dialog
end

-- 创建单个任务项
function TaskCalendar:createTaskItem(task, y)
    local FrameContainer = require("ui/widget/framecontainer")
    local Button = require("ui/widget/button")

    local item = FrameContainer:new{
        x = 20, y = y,
        width = Screen:getWidth() * 0.85,
        height = 70,
    }

    -- Priority color indicator
    local priority_colors = {
        urgent = {1, 0, 0},      -- red
        important = {1, 0.85, 0}, -- yellow
        normal = {0.5, 0.5, 0.5}, -- gray
    }
    local pcolor = priority_colors[task.priority] or priority_colors.normal

    -- Task title
    local title = TextWidget:new{
        text = task.title,
        face = Font:getFace("cfont", 22),
        color = 0, 0, 0,
        x = 15, y = y + 10,
    }
    item:addWidget(title)

    -- Due date/time
    local due_text = (task.date or "") .. " " .. (task.time or "")
    local due = TextWidget:new{
        text = due_text,
        face = Font:getFace("cfont", 14),
        color = 0.5, 0.5, 0.5,
        x = 15, y = y + 35,
    }
    item:addWidget(due)

    -- Complete button
    local complete_btn = Button:new{
        text = "✓ 完成",
        callback = function()
            self:handleComplete(task)
        end,
        x = Screen:getWidth() * 0.65,
        y = y + 15,
        width = 100,
        height = 40,
    }
    item:addWidget(complete_btn)

    return item
end

-- 处理完成按钮
function TaskCalendar:handleComplete(task)
    UIManager:show(ConfirmBox:new{
        text = "确定完成任务: " .. task.title .. "?",
        ok_callback = function()
            local success = self:completeTask(task.id)
            if success then
                UIManager:show(InfoMessage:new{
                    text = "✓ 任务已完成!",
                    duration = 2,
                })
                self:showTaskList()  -- Refresh list
            else
                UIManager:show(InfoMessage:new{
                    text = "✗ 操作失败",
                })
            end
        end,
    })
end

-- Event handler
function TaskCalendar:onTaskCalendar()
    self:showTaskList()
end

return TaskCalendar