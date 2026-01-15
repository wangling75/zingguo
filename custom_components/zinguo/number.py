from homeassistant.components.number import NumberEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    """设置数字平台"""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    api = data["api"]
    
    entities = []
    for mac in coordinator.data:
        # 1. 基础延时配置
        entities.append(ZinguoConfigNumber(coordinator, api, mac, "换气自动关闭", "ventilationAutoClose", 0, 90, "mdi:fan-clock"))
        entities.append(ZinguoConfigNumber(coordinator, api, mac, "取暖自动关闭", "warmingAutoClose", 0, 90, "mdi:heating-coil"))
        
        # 2. 系统校准与保护
        entities.append(ZinguoConfigNumber(coordinator, api, mac, "过温自动关闭温度", "overHeatAutoClose", 15, 45, "mdi:thermometer-alert"))
        entities.append(ZinguoConfigNumber(coordinator, api, mac, "温度显示校准", "temperatureCalibration", 0, 10, "mdi:tune-vertical"))
        
        # 3. 温控保护黑屏相关的数值设置
        entities.append(ZinguoBlackTimeNumber(coordinator, api, mac, "温控开启持续时间", "openTime"))
        entities.append(ZinguoBlackTimeNumber(coordinator, api, mac, "温控暂停持续时间", "pauseTime"))

        # 4. 新增：照明倒计时关闭 (时/分 转换)
        entities.append(ZinguoLightCountdown(coordinator, api, mac))

    async_add_entities(entities)

class ZinguoConfigNumber(NumberEntity):
    """通用滑块设置"""
    def __init__(self, coordinator, api, mac, name, key, v_min, v_max, icon):
        self.coordinator, self.api, self.mac, self.key = coordinator, api, mac, key
        self._attr_name = f"{name} ({mac[-4:]})"
        self._attr_native_min_value, self._attr_native_max_value = v_min, v_max
        self._attr_unique_id = f"zinguo_{mac}_{key}"
        self._attr_icon = icon

    @property
    def native_value(self):
        return self.coordinator.data.get(self.mac, {}).get(self.key)

    async def async_set_native_value(self, value):
        payload = {"mac": self.mac, "setParamter": True, self.key: int(value)}
        await self.api.send_control(payload)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.mac)}, "name": "峥果浴霸"}

class ZinguoBlackTimeNumber(NumberEntity):
    """黑屏温控模式的时间设置"""
    def __init__(self, coordinator, api, mac, name, key):
        self.coordinator, self.api, self.mac, self.key = coordinator, api, mac, key
        self._attr_name = f"{name} ({mac[-4:]})"
        self._attr_native_min_value, self._attr_native_max_value = 1, 30
        self._attr_unique_id = f"zinguo_{mac}_black_{key}"
        self._attr_icon = "mdi:clock-fast"

    @property
    def native_value(self):
        device = self.coordinator.data.get(self.mac, {})
        return device.get("blackSetting", {}).get(self.key, 5)

    async def async_set_native_value(self, value):
        device = self.coordinator.data.get(self.mac, {})
        curr_setting = device.get("blackSetting", {"status": True, "openTime": 5, "pauseTime": 5})
        curr_setting[self.key] = int(value)
        await self.api.set_protection(self.mac, curr_setting)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.mac)}, "name": "峥果浴霸"}

class ZinguoLightCountdown(NumberEntity):
    """照明延时关闭倒计时 (由原来的 TimeEntity 转换而来)"""
    def __init__(self, coordinator, api, mac):
        self.coordinator, self.api, self.mac = coordinator, api, mac
        self._attr_name = f"照明倒计时关闭 ({mac[-4:]})"
        self._attr_unique_id = f"zinguo_{mac}_light_countdown"
        self._attr_icon = "mdi:timer-sand"
        self._attr_native_min_value = 0
        self._attr_native_max_value = 1440  # 24小时
        self._attr_native_step = 1
        self._attr_native_unit_of_measurement = "min"

    @property
    def native_value(self):
        device = self.coordinator.data.get(self.mac, {})
        config = device.get("lightAutoClose", {})
        hr = config.get("stopHour", 0)
        mn = config.get("stopMinute", 0)
        return float(hr * 60 + mn)

    async def async_set_native_value(self, value):
        total_minutes = int(value)
        hr = total_minutes // 60
        mn = total_minutes % 60
        
        payload = {
            "mac": self.mac,
            "setParamter": True,
            "lightAutoClose": {
                "status": total_minutes > 0,
                "stopHour": hr,
                "stopMinute": mn
            }
        }
        await self.api.send_control(payload)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, self.mac)}, "name": "峥果浴霸"}
