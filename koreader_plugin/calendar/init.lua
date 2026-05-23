-- Kindle Calendar KOReader Plugin
-- 家长任务 -> Kindle孩子点击完成 -> 反馈

local Info = {
    name = "calendar",
    author = "Custom",
    version = "1.0",
    description = "家长任务确认",
}

local CalendarWidget = require("ui/widget/widget")
local FrameContainer = require("ui/widget/framecontainer")
local TextWidget = require("ui/widget/textwidget")
local IconWidget = require("ui/widget/iconwidget")
local GestureManager = require("ui/gesture")
local UIManager = require("ui/uimanager")
local Event = require("ui/event")
local G_reader = require("document~/documentregistry"):getReader()

local function get_appending_path()
    return "/mnt/us/calendar"
end

-- 获取任务列表
local function fetch_tasks()
    local socket = require("socket")
    local http = require("socket.http")
    local ltn12 = require("ltn12")

    local response = {}
    local url = "http://192.168.10.7:8082/api/events?pending=1"

    local request_body = ""
    local resp, code = http.request{
        url = url,
        method = "GET",
        sink = ltn12.sink.table(response),
    }

    if code == 200 then
        local json = require("json")
        return json.decode(table.concat(response))
    end
    return {}
end

-- 标记任务完成
local function complete_task(task_id)
    local socket = require("socket")
    local http = require("socket.http")
    local ltn12 = require("ltn12")

    local url = "http://192.168.10.7:8082/api/events/" .. task_id
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

-- 任务项widget
local TaskItem = FrameContainer:new{
    task = nil,
    callback = nil,
}

function TaskItem:init()
    self[1] = TextWidget:new{
        text = self.task.title,
        face = Font:getFace("cfont", 22),
    }
    self[2] = TextWidget:new{
        text = self.task.date .. " " .. (self.task.time or ""),
        face = Font:getFace("cfont", 14),
        color = 8,
    }
end

-- 主界面
local CalendarDialog = FrameContainer:new{
    width = Screen:width(),
    height = Screen:height(),
    background = Color:new(1, 1, 1),
}

function CalendarDialog:init()
    -- Header
    self:addWidget(TextWidget:new{
        text = "📋 任务列表",
        face = Font:getFace("cfont", 28),
        x = 10, y = 10,
    })

    -- Load tasks
    local tasks = fetch_tasks()

    -- Task list
    local y = 60
    for i, task in ipairs(tasks) do
        local task_w = FrameContainer:new{
            x = 10, y = y,
            width = Screen:width() - 20,
            height = 50,
            background = Color:new(0.95, 0.95, 0.95),
        }

        task_w:addWidget(TextWidget:new{
            text = task.title,
            face = Font:getFace("cfont", 20),
            x = 15, y = y + 5,
        })

        task_w:addWidget(TextWidget:new{
            text = task.date,
            face = Font:getFace("cfont", 14),
            x = 15, y = y + 25,
            color = 8,
        })

        -- Complete button
        task_w:addWidget(GestureManager:new{
            x = Screen:width() - 100, y = y,
            width = 80, height = 50,
            ges = "tap",
            handler = function()
                complete_task(task.id)
                UIManager:close(self)
                UIManager:show(CalendarDialog:new())
            end,
        })

        self:addWidget(task_w)
        y = y + 55
    end

    -- Refresh button
    self:addWidget(GestureManager:new{
        x = 10, y = Screen:height() - 60,
        width = 120, height = 50,
        ges = "tap",
        handler = function()
            UIManager:close(self)
            UIManager:show(CalendarDialog:new())
        end,
    })
end

-- Show calendar
local function show_calendar()
    UIManager:show(CalendarDialog:new())
end

return {
    Info = Info,
    show = show_calendar,
}