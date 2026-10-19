"""Home Assistant representation of an Sunology device."""
from .const import SmartMeterPhase, SmartMeterTarifIndex, ElectricalDataFeature, FlowWorkingModes, FeatureFlowNodeModes, ContactorMode, ContactorStatus, DOMAIN as SUNOLOGY_DOMAIN, PACKAGE_NAME
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntry
from homeassistant.helpers import device_registry as dr
from collections.abc import Callable
from homeassistant.helpers.device_registry import DeviceInfo as _DeviceInfo

# via_device (identifier tuple) is deprecated from HA 2026.8 and removed in 2027.8;
# via_device_id does not exist before 2026.8. hacs.json supports 2024.10+, so pick
# the form the running core understands.
_HA_HAS_VIA_DEVICE_ID = "via_device_id" in getattr(_DeviceInfo, "__annotations__", {})
from typing import List
import logging

_LOGGER = logging.getLogger(PACKAGE_NAME)

class SunologyAbstractDevice():
    """Home Assistant representation of a Sunology abstract device."""

    def __init__(self, raw_device):
        """Initialize PLAYMax device."""
        self._unique_id: str = raw_device['id']
        self._software_version: str = raw_device['fwVersion'] if 'fwVersion' in raw_device.keys() else None
        self._hw_version: str = raw_device['hwVersion'] if 'hwVersion' in raw_device.keys() else None
        self._device_entry_id = None
        self._parent_id: str = raw_device['parentId'] if 'parentId' in raw_device.keys() else None
        self._via_device_id: str | None = None
        self._name: str = raw_device['name'] if 'name' in raw_device.keys() else f"{self.model_name} {self.device_id}"
        self._rssi: int = raw_device['rssi'] if 'rssi' in raw_device.keys() else raw_device['rssiWifi'] if 'rssiWifi' in raw_device.keys() else None
        self._bssid: int = raw_device['bssid'] if 'bssid' in raw_device.keys() else None
        self._wifiIP: int = raw_device['wifiIP'] if 'wifiIP' in raw_device.keys() else None
        self._ethIP: int = raw_device['ethIP'] if 'ethIP' in raw_device.keys() else None

    @property
    def default_manufacturer(self) -> str:
        """Get the default_manufacturer."""
        return "Sunology"

    @property
    def manufacturer(self) -> str:
        """Get the manufacturer."""
        return "Sunology"
    
    @property
    def model_name(self) -> str:
        """Get the model."""
        return "Abstract"

    @property
    def name(self) -> str:
        """Get the name."""
        return self._name

    @property
    def parent_id(self) -> str | None:
        """Get the Sunology id of the parent device, if any."""
        return self._parent_id

    @property
    def sw_version(self) -> str:
        """Get the software version."""
        return str(self._software_version)

    @property
    def hw_version(self) -> str:
        """Get the hardware version."""
        return str(self._hw_version)

    @property
    def device_id(self) -> str:
        """Get the device unique id."""
        return self._unique_id
    
    @property
    def unique_id(self):
        """Get the unique id."""
        return {(SUNOLOGY_DOMAIN, self._unique_id)}

    @property
    def device_entry_id(self):
        return self._device_entry_id
    
    @device_entry_id.setter
    def device_entry_id(self, device_entry_id):
        """ change auth_token """
        self._device_entry_id = device_entry_id

    @property
    def rssi(self):
        return self._rssi

    @property
    def bssid(self):
        return self._bssid
    
    @property
    def wifiIP(self):
        return self._wifiIP

    @property
    def ethIP(self):
        return self._ethIP

    def update_product(self, raw_event):
        if 'rssi' in raw_event.keys():
            self._rssi = raw_event['rssi']
        
        elif 'rssiWifi' in raw_event.keys():
            self._rssi = raw_event['rssiWifi']
        
        if 'swVersion' in raw_event.keys():
            self._software_version = raw_event['swVersion']

        if 'bssid' in raw_event.keys():
            self._bssid = raw_event['bssid']

        if 'wifiIP' in raw_event.keys():
            self._wifiIP = raw_event['wifiIP']

        if 'ethIP' in raw_event.keys():
            self._ethIP = raw_event['ethIP']

    @property
    def device_info(self):
        """Return the device info."""
        dev_info = DeviceInfo(
            name=self.name,
            identifiers=self.unique_id,
            manufacturer=self.manufacturer,
            model=self.model_name,
            sw_version=self.sw_version,
            hw_version=self.hw_version,
        )
        if _HA_HAS_VIA_DEVICE_ID:
            # HA >= 2026.8: link to the parent by registry id, known once register()
            # ran. HA rejects (does not add the entity) a via_device_id that is not a
            # registered device, so it is only set when the parent was found.
            if self._via_device_id is not None:
                dev_info["via_device_id"] = self._via_device_id
        elif self._parent_id is not None:
            # HA < 2026.8 only knows the identifier tuple form.
            dev_info["via_device"] = (SUNOLOGY_DOMAIN, self._parent_id)
        return dev_info

    def register(self, device_registry: dr.DeviceRegistry, entry, via_device_id: str | None) -> DeviceEntry:
        """Register the device in the device registry, linked to its parent device id."""
        self._via_device_id = via_device_id
        device_entry = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            **self.device_info
        )
        self.device_entry_id = device_entry.id
        return device_entry

class SolarEventInterface():
    """Sunology extra porperties for events."""
    def __init__(self, raw_device):
        pass
    
    @property
    def pvP(self):
        """Return the pvP value"""
        return self._pvP
    
    @property
    def miP(self):
        """Return the miP value"""
        return self._miP
    
    @property
    def mppts_data(self):
        """Return the mppts_data dictionary"""
        return getattr(self, '_mppts_data', {})
    
    def solar_event_update(self, data):
        # A missing field keeps the last known value instead of resetting it to None.
        if 'miP' in data:
            self._miP = data['miP']
        if 'pvP' in data:
            self._pvP = data['pvP']
        if 'miP' not in data and 'pvP' not in data:
            _LOGGER.debug("Solar event without miP / pvP for %s", data.get('id'))
        if 'mppts' in data.keys():
            for mppt_data in data['mppts']:
                mppt_index = mppt_data['mpptIndex']
                if hasattr(self, "_mppts_data") and mppt_index in self._mppts_data:
                    self._mppts_data[mppt_index].update_mppt_data(mppt_data)

class BatteryPackInterface():
    """Sunology extra porperties for events."""
    def __init__(self, raw_device):
        self._capacity = None
        self._maxInput = None
        self._maxOutput = None
    
    @property
    def capacity(self) -> int:
        """Get the capacity."""
        return self._capacity

    @capacity.setter
    def capacity(self, capacity):
        """Set the capacity."""
        self._capacity = capacity
    
    @property
    def maxInput(self) -> int:
        """Get the maxInput."""
        return self._maxInput
    
    @maxInput.setter
    def maxInput(self, maxInput):
        """Set the maxInput."""
        self._maxInput = maxInput

    @property
    def maxOutput(self) -> int:
        """Get the maxOutput."""
        return self._maxOutput
    
    @maxOutput.setter
    def maxOutput(self, maxOutput):
        """Set the maxInput."""
        self._maxOutput = maxOutput



class BatteryEventInterface():
    """Sunology extra porperties for events."""
    def __init__(self, raw_device):
        self._cellsTmp = None
        self._radTmp = None
        self._targetPow = None
        self._dcCurrent = None
        self._dcVoltage = None
        self._energyCons = None
        self._energyProd = None
        self._batTmp = None
        self._batPct = None
        self._batP = None

    @property
    def batP(self):
        """Return the batP value"""
        return self._batP
    
    @property
    def batPct(self):
        """Return the batPct value"""
        return self._batPct
    
    @property
    def batTmp(self):
        """Return the batTmp value"""
        return self._batTmp
    
    @property
    def cellsTmp(self):
        """return the cellsTmp value"""
        return self._cellsTmp
 
    @property
    def radTmp(self):
        """return the radTmp value"""
        return self._radTmp
 
    @property
    def targetPow(self):
        """return the targetPow value"""
        return self._targetPow
 
    @property
    def dcCurrent(self):
        """return the dcCurrent value"""
        return self._dcCurrent
    
    @property
    def dcVoltage(self):
        """return the dcVoltage value"""
        return self._dcVoltage
 
    @property
    def energyCons(self):
        """return the energyCons value"""
        return self._energyCons
 
    @property
    def energyProd(self):
        """return the energyProd value"""
        return self._energyProd

    def battery_event_update(self, data):
        """Update the battery values from a batteryEvent (STOREY) or solarEvent (PLAY Max).

        The STOREY sends the battery power as `batPow`, the PLAY Max as `batP`
        (fw-sconnect PlayMaxDto). A missing field keeps the last known value.
        """
        if 'batPow' in data:
            self._batP = data['batPow']
        elif 'batP' in data:
            self._batP = data['batP']
        else:
            _LOGGER.debug("Battery event without battery power for %s", data.get('id'))
        if 'batPct' in data:
            self._batPct = data['batPct']
        if 'batTmp' in data:
            self._batTmp = data['batTmp']
        if 'cellsTmp' in data.keys():
            self._cellsTmp = data['cellsTmp']
        if 'radTmp' in data.keys():
            self._radTmp = data['radTmp']
        if 'targetPow' in data.keys():
            self._targetPow = data['targetPow']
        if 'dcCurrent' in data.keys():
            self._dcCurrent = data['dcCurrent']
        if 'dcVoltage' in data.keys():
            self._dcVoltage = data['dcVoltage']
        if 'energyCons' in data.keys():
            self._energyCons = data['energyCons']
        if 'energyProd' in data.keys():
            self._energyProd = data['energyProd']



class PLAY(SunologyAbstractDevice, SolarEventInterface):
    """Home Assistant representation of a Sunology device PLAY."""

    def __init__(self, raw_play):
        """Initialize PLAYMax device."""
        super().__init__(raw_play)
        SolarEventInterface.__init__(self, raw_play)
        self._pvP = None
        self._miP = None
        self._mppts_data = {
            0: MpptInterface()
        }

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Garden"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "PLAY"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info


    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class CITY(SunologyAbstractDevice, SolarEventInterface):
    """Home Assistant representation of a Sunology device CITY."""

    def __init__(self, raw_play):
        """Initialize CITY device."""
        super().__init__(raw_play)
        SolarEventInterface.__init__(self, raw_play)
        self._pvP = None
        self._miP = None
        self._mppts_data = {
            0: MpptInterface()
        }

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Garden"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "CITY"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info


    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class HOMEInverter(SunologyAbstractDevice, SolarEventInterface):
    """Home Assistant representation of a Sunology device PLAY."""

    def __init__(self, raw_play):
        """Initialize Home solar inverter device."""
        super().__init__(raw_play)
        SolarEventInterface.__init__(self, raw_play)
        self._pvP = None
        self._miP = None
        self._acVoltage = None
        self._mppts_data = {
            0:   MpptInterface(),
            1:   MpptInterface()
        }


    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Garden"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "HOME Solar"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info


    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class StoreyMaster(SunologyAbstractDevice, BatteryPackInterface, BatteryEventInterface):
    """Home Assistant representation of a Sunology device PLAY."""

    def __init__(self, raw_storey):
        """Initialize PLAYMax device."""
        super().__init__(raw_storey)

        BatteryPackInterface.__init__(self, raw_storey)
        BatteryEventInterface.__init__(self, raw_storey)
        self._unique_id: str = f"{raw_storey['id']}"
        self._status = None
        self._acVoltage = None

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Livinroom"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "Storey Master"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info

    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

    @property
    def acVoltage(self):
        """return the acVoltage value"""
        return self._acVoltage

        
    @acVoltage.setter
    def acVoltage(self, acVoltage):
        """Set the acVoltage value"""
        self._acVoltage = acVoltage
    
    @property
    def status(self):
        """return the status value"""
        return self._status
    
    @status.setter
    def status(self, status):
        """Set the status value"""
        self._status = status

class StoreyPack(SunologyAbstractDevice, BatteryPackInterface, BatteryEventInterface):
    """Home Assistant representation of a Sunology device PLAY."""

    def __init__(self, raw_storey_pack, pack_index):
        """Initialize PLAYMax device."""
        super().__init__(raw_storey_pack)
        BatteryPackInterface.__init__(self, raw_storey_pack)
        BatteryEventInterface.__init__(self, raw_storey_pack)
        self._unique_id: str = f"{raw_storey_pack['id']}#{pack_index}"
        self._parent_id: str = f"{raw_storey_pack['id']}"
        self._name: str = raw_storey_pack['name'] if 'name' in raw_storey_pack.keys() else f"{self.model_name} {self._unique_id}"


    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Livinroom"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "Storey Pack"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info

    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class PLAYMax(SunologyAbstractDevice, SolarEventInterface, BatteryEventInterface):
    """Home Assistant representation of a Sunology device PLAYMax."""

    def __init__(self, raw_playmax):
        """Initialize PLAYMax device."""
        super().__init__(raw_playmax)
        SolarEventInterface.__init__(self, raw_playmax)
        BatteryEventInterface.__init__(self, raw_playmax)
        self._batP = None
        self._batPct = None
        self._batTmp = None
        self._pvP = None
        self._miP = None

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Garden"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "PLAY Max"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info


    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class SmartMeter_ElectricalData():
    """Home Assistant representation of a Sunology SmartMeter_electrical_data property."""

    def __init__(self, current=None, voltage=None, power_factor=None, power=None, apparent_power=None, conso_tot=None, prod_tot=None):
        """Initialize SmartMeter_electrical_data property."""
        self._current = current
        self._voltage = voltage
        self._power_factor = power_factor
        self._power = power
        self._apparent_power = apparent_power
        self._conso_tot = conso_tot
        self._prod_tot = prod_tot

    @property
    def current(self):
        """Get the current"""
        return self._current

    @property
    def voltage(self):
        """Get the voltage"""
        return self._voltage

    @property
    def power_factor(self):
        """Get the power_factor"""
        return self._power_factor

    @property
    def power(self):
        """Get the power"""
        return self._power

    @property
    def apparent_power(self):
        """Get the apparent_power"""
        return self._apparent_power

    @property
    def conso_tot(self):
        """Get the conso_tot"""
        return self._conso_tot

    @property
    def prod_tot(self):
        """Get the prod_tot"""
        return self._prod_tot

    def update_electrical_data(self, raw_electrical_data):
        if 'current' in raw_electrical_data.keys():
            self._current = raw_electrical_data['current']
        if 'voltage' in raw_electrical_data.keys():
            self._voltage = raw_electrical_data['voltage']
        if 'powerFactor' in raw_electrical_data.keys():
            self._power_factor = raw_electrical_data['powerFactor']
        if 'power' in raw_electrical_data.keys():
            self._power = raw_electrical_data['power']
        if 'apparentPower' in raw_electrical_data.keys():
            self._apparent_power = raw_electrical_data['apparentPower']
        if 'consoTot' in raw_electrical_data.keys():
            self._conso_tot = raw_electrical_data['consoTot']
        if 'prodTot' in raw_electrical_data.keys():
            self._prod_tot = raw_electrical_data['prodTot']

class MpptInterface():
    """Home Assistant representation of a Sunology MPPT property."""

    def __init__(self, current=None, voltage=None, power=None, prod_tot=None):
        """Initialize MPPT property."""
        self._current = current
        self._voltage = voltage
        self._power = power
        self._prod_tot = prod_tot

    @property
    def current(self):
        """Get the current"""
        return self._current

    @property
    def voltage(self):
        """Get the voltage"""
        return self._voltage

    @property
    def power(self):
        """Get the power"""
        return self._power

    @property
    def prod_tot(self):
        """Get the prod_tot"""
        return self._prod_tot
    
    def update_mppt_data(self, raw_mppt_data):
        """Update MPPT data from raw event data."""
        if 'pvI' in raw_mppt_data.keys():
            self._current = raw_mppt_data['pvI']
        if 'pvV' in raw_mppt_data.keys():
            self._voltage = raw_mppt_data['pvV']
        if 'pvP' in raw_mppt_data.keys():
            self._power = raw_mppt_data['pvP']
        if 'totalGen' in raw_mppt_data.keys():
            self._prod_tot = raw_mppt_data['totalGen']


class SmartMeter_ElectricalDataFeatures():
    """Home Assistant representation of a Sunology SmartMeter_electrical_data_feature property."""

    def __init__(self, electricalData=None, electricalDataP1=None, electricalDataP2=None, electricalDataP3=None, 
                    flow_ready=None, estimated_power_usage=None, min_active_time=None, max_active_time=None, 
                    min_energy_usage=None, max_energy_usage=None, priority=None):
        """Initialize SmartMeter_electrical_data property."""
        self._flow_ready = flow_ready
        self._estimated_power_usage = estimated_power_usage
        self._min_active_time = min_active_time
        self._max_active_time = max_active_time
        self._min_energy_usage = min_energy_usage
        self._max_energy_usage = max_energy_usage
        self._priority = priority
        self._electricalData = electricalData
        self._electricalDataP1 = electricalDataP1
        self._electricalDataP2 = electricalDataP2
        self._electricalDataP3 = electricalDataP3
    
    @property
    def flow_ready(self):
        """Get the flow_ready"""
        return self._flow_ready

    @property
    def estimated_power_usage(self):
        """Get the estimated_power_usage"""
        return self._estimated_power_usage

    @property
    def min_active_time(self):
        """Get the min_active_time"""
        return self._min_active_time

    @property
    def max_active_time(self):
        """Get the max_active_time"""
        return self._max_active_time

    @property
    def min_energy_usage(self):
        """Get the min_energy_usage"""
        return self._min_energy_usage

    @property
    def max_energy_usage(self):
        """Get the max_energy_usage"""
        return self._max_energy_usage

    @property
    def priority(self):
        """Get the priority"""
        return self._priority
    
    @property
    def electricalData(self):
        """Get the electricalData"""
        return self._electricalData

    @property
    def electricalDataP1(self):
        """Get the electricalDataP1"""
        return self._electricalDataP1

    @property
    def electricalDataP2(self):
        """Get the electricalDataP2"""
        return self._electricalDataP2

    @property
    def electricalDataP3(self):
        """Get the electricalDataP3"""
        return self._electricalDataP3

    def update_electrical_data_feature(self, raw_electrical_data_feature):
        if 'electricalData' in raw_electrical_data_feature.keys():
            self._electricalData = raw_electrical_data_feature['electricalData']
        else:
            self._electricalData = ElectricalDataFeature.UNUSED

        if 'electricalDataP1' in raw_electrical_data_feature.keys():
            self._electricalDataP1 = raw_electrical_data_feature['electricalDataP1']
        else:
            self._electricalDataP1 = ElectricalDataFeature.UNUSED

        if 'electricalDataP2' in raw_electrical_data_feature.keys():
            self._electricalDataP2 = raw_electrical_data_feature['electricalDataP2']
        else:
            self._electricalDataP2 = ElectricalDataFeature.UNUSED

        if 'electricalDataP3' in raw_electrical_data_feature.keys():
            self._electricalDataP3 = raw_electrical_data_feature['electricalDataP3']
        else:
            self._electricalDataP3 = ElectricalDataFeature.UNUSED

class FlowDevice_FlowNodeConfig():
    """Home Assistant representation of a Sunology SmartMeter_electrical_data_feature property."""

    def __init__(self, enabled=None, mode=None, priority=None, type=None, autoCalib=None, efficiency=None,
                 dailyRuntimeEn=None, runtimeMin=None, runtimeMax=None, dailyEnergyEn=None,
                 energyMin=None, energyMax=None, minOnTime=None, minCons=None, maxCons=None,
                 minProd=None, maxProd=None):
        """Initialize SmartMeter_electrical_data property."""
        self._enabled = enabled
        self._mode = mode
        self._priority = priority
        self._type = type
        self._autoCalib = autoCalib
        self._efficiency = efficiency
        self._dailyRuntimeEn = dailyRuntimeEn
        self._runtimeMin = runtimeMin
        self._runtimeMax = runtimeMax
        self._dailyEnergyEn = dailyEnergyEn
        self._energyMin = energyMin
        self._energyMax = energyMax
        self._minOnTime = minOnTime
        self._minCons = minCons
        self._maxCons = maxCons
        self._minProd = minProd
        self._maxProd = maxProd
    
    @property
    def enabled(self):
        """True if the device is part of the Flow (false will be skipped for any feature)"""
        return self._enabled

    @property
    def mode(self):
        """Get the mode"""
        return self._mode

    @property
    def priority(self):
        """Get the priority"""
        return self._priority

    @property
    def type(self):
        """Get the type"""
        return self._type

    @property
    def autoCalib(self):
        """True if the device supports auto calibration (power measurement for consumer)"""
        return self._autoCalib

    @property
    def efficiency(self):
        """Device efficiency in percent. i.e. 80.3 = 80.3%"""
        return self._efficiency

    @property
    def dailyRuntimeEn(self):
        """True if the device supports daily runtime feature"""
        return self._dailyRuntimeEn

    @property
    def runtimeMin(self):
        """Minimum daily active time in minutes"""
        return self._runtimeMin

    @property
    def runtimeMax(self):
        """Maximum daily active time in minutes"""
        return self._runtimeMax

    @property
    def dailyEnergyEn(self):
        """True if the device supports daily energy feature"""
        return self._dailyEnergyEn

    @property
    def energyMin(self):
        """Minimum daily energy usage in Wh"""
        return self._energyMin

    @property
    def energyMax(self):
        """Maximum daily energy usage in Wh"""
        return self._energyMax

    @property
    def minOnTime(self):
        """Minimal on time in seconds to prevent hardware degradation"""
        return self._minOnTime

    @property
    def minCons(self):
        """Minimum consumption power usage"""
        return self._minCons

    @property
    def maxCons(self):
        """Maximum consumption power usage"""
        return self._maxCons

    @property
    def minProd(self):
        """Minimum production power usage"""
        return self._minProd

    @property
    def maxProd(self):
        """Maximum production power usage"""
        return self._maxProd

    def update_flowNode(self, raw_flowNode):
        if 'enabled' in raw_flowNode.keys():
            self._enabled = raw_flowNode['enabled']
        if 'mode' in raw_flowNode.keys():
            self._mode = raw_flowNode['mode']
        if 'priority' in raw_flowNode.keys():
            self._priority = raw_flowNode['priority']
        if 'type' in raw_flowNode.keys():
            self._type = raw_flowNode['type']
        if 'autoCalib' in raw_flowNode.keys():
            self._autoCalib = raw_flowNode['autoCalib']
        if 'efficiency' in raw_flowNode.keys():
            self._efficiency = raw_flowNode['efficiency']
        if 'dailyRuntimeEn' in raw_flowNode.keys():
            self._dailyRuntimeEn = raw_flowNode['dailyRuntimeEn']
        if 'runtimeMin' in raw_flowNode.keys():
            self._runtimeMin = raw_flowNode['runtimeMin']
        if 'runtimeMax' in raw_flowNode.keys():
            self._runtimeMax = raw_flowNode['runtimeMax']
        if 'dailyEnergyEn' in raw_flowNode.keys():
            self._dailyEnergyEn = raw_flowNode['dailyEnergyEn']
        if 'energyMin' in raw_flowNode.keys():
            self._energyMin = raw_flowNode['energyMin']
        if 'energyMax' in raw_flowNode.keys():
            self._energyMax = raw_flowNode['energyMax']
        if 'minOnTime' in raw_flowNode.keys():
            self._minOnTime = raw_flowNode['minOnTime']
        if 'minCons' in raw_flowNode.keys():
            self._minCons = raw_flowNode['minCons']
        if 'maxCons' in raw_flowNode.keys():
            self._maxCons = raw_flowNode['maxCons']
        if 'minProd' in raw_flowNode.keys():
            self._minProd = raw_flowNode['minProd']
        if 'maxProd' in raw_flowNode.keys():
            self._maxProd = raw_flowNode['maxProd']

class SmartMeter_IndexesErl():
    """Home Assistant representation of a Sunology SmartMeter_IndexesErl property."""

    def __init__(self):
        """Initialize SmartMeter_electrical_data property."""
        self._contract = None
        self._current_tarif = None
        self._energy_consumed_total = None
        self._energy_produced_total = None
        self._energy_consumed_indexed = {
            SmartMeterTarifIndex.INDEX_1: None,
            SmartMeterTarifIndex.INDEX_2: None,
            SmartMeterTarifIndex.INDEX_3: None,
            SmartMeterTarifIndex.INDEX_4: None,
            SmartMeterTarifIndex.INDEX_5: None,
            SmartMeterTarifIndex.INDEX_6: None,
            SmartMeterTarifIndex.INDEX_7: None,
            SmartMeterTarifIndex.INDEX_8: None,
            SmartMeterTarifIndex.INDEX_9: None,
            SmartMeterTarifIndex.INDEX_10: None
        }

    @property
    def contract(self):
        """get the contract"""
        return self._contract

    @property
    def current_tarif(self):
        """get the current_tarif"""
        return self._current_tarif

    @property
    def energy_consumed_total(self):
        """get the energy_consumed_total"""
        return self._energy_consumed_total

    @property
    def energy_produced_total(self):
        """get the energy_produced_total"""
        return self._energy_produced_total

    @property
    def energy_consumed_indexed(self):
        """get the energy_consumed_indexed"""
        return self._energy_consumed_indexed

    def update_indexes_erl(self, raw_indexes_erl):
        if 'contract' in raw_indexes_erl.keys():
            self._contract = raw_indexes_erl['contract']
        if 'currentTarif' in raw_indexes_erl.keys():
            self._current_tarif = raw_indexes_erl['currentTarif']
        if 'energyConsumedTotal' in raw_indexes_erl.keys():
            self._energy_consumed_total = raw_indexes_erl['energyConsumedTotal']
        if 'energyProducedTotal' in raw_indexes_erl.keys():
            self._energy_produced_total = raw_indexes_erl['energyProducedTotal']
        if 'energyConsumedIdx1' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_1] = raw_indexes_erl['energyConsumedIdx1']
        if 'energyConsumedIdx2' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_2] = raw_indexes_erl['energyConsumedIdx2']
        if 'energyConsumedIdx3' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_3] = raw_indexes_erl['energyConsumedIdx3']
        if 'energyConsumedIdx4' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_4] = raw_indexes_erl['energyConsumedIdx4']
        if 'energyConsumedIdx5' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_5] = raw_indexes_erl['energyConsumedIdx5']
        if 'energyConsumedIdx6' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_6] = raw_indexes_erl['energyConsumedIdx6']
        if 'energyConsumedIdx7' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_7] = raw_indexes_erl['energyConsumedIdx7']
        if 'energyConsumedIdx8' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_8] = raw_indexes_erl['energyConsumedIdx8']
        if 'energyConsumedIdx9' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_9] = raw_indexes_erl['energyConsumedIdx9']
        if 'energyConsumed_Ix10' in raw_indexes_erl.keys():
            self._energy_consumed_indexed[SmartMeterTarifIndex.INDEX_10] = raw_indexes_erl['energyConsumedIdx10']

class OnOffDevice(SunologyAbstractDevice):
    """Home Assistant representation of a Sunology on/off device driven by the Flow."""

    def __init__(self, raw_device, set_flowNodeMode_callback: Callable[[str], None] = None):
        """Initialize on/off device."""
        super().__init__(raw_device)

        self._electrical_data = {
            SmartMeterPhase.ALL: SmartMeter_ElectricalData()
        }
        self._state = None
        # Sent by the hub on every onOffEvent of a device that is a Flow node
        # (Device::attributesToCJson, fw-sconnect): minutes of runtime today and the
        # power the Flow currently grants the device.
        self._runtime_on = None
        self._target_power = None
        self._flowNodeConfig = FlowDevice_FlowNodeConfig()
        self._features = SmartMeter_ElectricalDataFeatures()
        if 'features' in raw_device.keys():
            self._features.update_electrical_data_feature(raw_device['features'])
            if "flowNode" in raw_device["features"].keys():
                self._flowNodeConfig.update_flowNode(raw_device["features"]["flowNode"])

        self._set_flowNodeMode_callback = set_flowNodeMode_callback

    @property
    def state(self):
        """Get the state."""
        return self._state

    @property
    def runtime_on(self):
        """Minutes the device has been on today, as counted by the Flow."""
        return self._runtime_on

    @property
    def target_power(self):
        """Power in W the Flow currently grants the device."""
        return self._target_power

    @property
    def supported_flow_node_modes(self) -> List[str]:
        """Get the flow node modes the hardware can actually honour."""
        return [e.name for e in FeatureFlowNodeModes]

    @property
    def has_energy_metering(self) -> bool:
        """True when the device reports a cumulated energy counter."""
        return True

    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info

    @property
    def flowNodeConfig(self):
        """Get the flowMode"""
        return self._flowNodeConfig

    @property
    def electrical_data(self):
        """Get the electrical_data"""
        return self._electrical_data

    @property
    def features(self):
        """Get the features"""
        return self._features

    def update_onOff_event(self, raw_onOff_event):
        if "onOff" in raw_onOff_event.keys():
            self._state = raw_onOff_event['onOff']
        if "runtimeOn" in raw_onOff_event.keys():
            self._runtime_on = raw_onOff_event['runtimeOn']
        if "targetPower" in raw_onOff_event.keys():
            self._target_power = raw_onOff_event['targetPower']
        if "electricalData" in raw_onOff_event.keys():
            self.electrical_data[SmartMeterPhase.ALL].update_electrical_data(raw_onOff_event['electricalData'])

    async def _set_flowNodeMode(self, mode: str):
        """Set the flow node mode of the device."""
        if self._set_flowNodeMode_callback is None:
            _LOGGER.error("No callback set for _set_flowNodeMode")
            return
        await self._set_flowNodeMode_callback(mode)

    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

    def update_product(self, raw_event):
        super().update_product(raw_event)
        if "features" in raw_event.keys():
            if "flowNode" in raw_event["features"].keys():
                self._flowNodeConfig.update_flowNode(raw_event["features"]["flowNode"])
            if self._features is None:
                self._features = SmartMeter_ElectricalDataFeatures()
            self._features.update_electrical_data_feature(raw_event["features"])

class SmartOutlet(OnOffDevice):
    """Home Assistant representation of a Sunology device Smart."""

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Livingroom"

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "Pulse"

class LegrandContactor(OnOffDevice):
    """Home Assistant representation of a Sunology TAP, the Legrand day/night contactor."""

    def __init__(self, raw_device, set_flowNodeMode_callback: Callable[[str], None] = None):
        """Initialize TAP device."""
        super().__init__(raw_device, set_flowNodeMode_callback)
        self._contactor_mode = None

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Livingroom"

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "TAP"

    @property
    def manufacturer(self) -> str:
        """Get the manufacturer."""
        # The hub reports manufacturerName "Sunology" for every device it relays,
        # including this one. The TAP is a Legrand contactor, don't relay that error.
        return "Legrand"

    @property
    def supported_flow_node_modes(self) -> List[str]:
        """Get the flow node modes the hardware can actually honour.

        ZIGBEE_INTERFACE_setPower() maps a zero target power to LEGRAND_MODE_AUTO, never
        to LEGRAND_MODE_OFF: the firmware cannot open the contactor on request. Offering
        FORCED_OFF would return the contactor to AUTO, so it would close again on the
        off-peak contact. Only expose what the hardware honours.
        """
        return [FeatureFlowNodeModes.FLOW.name, FeatureFlowNodeModes.FORCED_ON.name]

    @property
    def has_energy_metering(self) -> bool:
        """True when the device reports a cumulated energy counter.

        The TAP binds ELECTRICAL_MEASUREMENT only, never METERING: it reports power but
        no energy counter, ever.
        """
        return False

    @property
    def contactor_mode(self):
        """Get the contactor mode reported by the device."""
        return self._contactor_mode

    @property
    def status(self):
        """STREAM app status, see ContactorStatus."""
        if self._contactor_mode is None:
            return None
        if self._contactor_mode == ContactorMode.ON:
            return ContactorStatus.FORCED_ON
        if self._contactor_mode == ContactorMode.AUTO:
            return ContactorStatus.ACTIVE if self._state else ContactorStatus.IDLE
        return ContactorStatus.UNKNOWN

    def update_onOff_event(self, raw_onOff_event):
        super().update_onOff_event(raw_onOff_event)
        if "contactorMode" in raw_onOff_event.keys():
            self._contactor_mode = raw_onOff_event['contactorMode']

class LinkyTransmitter(SunologyAbstractDevice):
    """Home Assistant representation of a Sunology device Smart."""

    def __init__(self, raw_smartmeter):
        """Initialize STREAM Link device."""
        super().__init__(raw_smartmeter)
        self._app_power_usage = None
        self._app_power_prod = None
        self._indexes_erl = SmartMeter_IndexesErl()

    @property
    def app_power_usage(self):
        """Get the app_power_usage."""
        return self._app_power_usage

    @property
    def app_power_prod(self):
        """Get the app_power_usage."""
        return self._app_power_prod

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Garage"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "STREAM Link"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info

    @property
    def indexes_erl(self):
        """Get the electrical_data"""
        return self._indexes_erl

    def update_gridevent(self, raw_grid_event):
        if "appPowerUsage" in raw_grid_event.keys():
            self._app_power_usage = raw_grid_event['appPowerUsage']
        if "appPowerProd" in raw_grid_event.keys():
            self._app_power_prod = raw_grid_event['appPowerProd']
        if "indexesErl" in raw_grid_event.keys():
            self.indexes_erl.update_indexes_erl(raw_grid_event['indexesErl'])

    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class SmartMeter_3P(SunologyAbstractDevice):
    """Home Assistant representation of a Sunology device Smart."""

    def __init__(self, raw_smartmeter):
        """Initialize SmartMeter_3 device."""
        super().__init__(raw_smartmeter)
        self._freq = None
        self._electrical_data = {
            SmartMeterPhase.ALL:       SmartMeter_ElectricalData(),
            SmartMeterPhase.PHASE_1:   SmartMeter_ElectricalData(),
            SmartMeterPhase.PHASE_2:   SmartMeter_ElectricalData(),
            SmartMeterPhase.PHASE_3:   SmartMeter_ElectricalData()
        }
        if 'features' in raw_smartmeter.keys():
            self._features = SmartMeter_ElectricalDataFeatures()
            self._features.update_electrical_data_feature(raw_smartmeter['features'])

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Garden"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        return "STREAM Meter"
    
    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info

    @property
    def freq(self):
        """Get the frequency"""
        return self._freq
    
    @property
    def electrical_data(self):
        """Get the electrical_data"""
        return self._electrical_data
    
    @property
    def features(self):
        """Get the features"""
        return self._features

    def update_gridevent(self, raw_grid_event):
        if "freq" in raw_grid_event.keys():
            self._freq = raw_grid_event['freq']
        if "electricalData" in raw_grid_event.keys():
            self.electrical_data[SmartMeterPhase.ALL].update_electrical_data(raw_grid_event['electricalData'])
        if "electricalDataP1" in raw_grid_event.keys():
            self.electrical_data[SmartMeterPhase.PHASE_1].update_electrical_data(raw_grid_event['electricalDataP1'])
        if "electricalDataP2" in raw_grid_event.keys():
            self.electrical_data[SmartMeterPhase.PHASE_2].update_electrical_data(raw_grid_event['electricalDataP2'])
        if "electricalDataP3" in raw_grid_event.keys():
            self.electrical_data[SmartMeterPhase.PHASE_3].update_electrical_data(raw_grid_event['electricalDataP3'])
    
    def update_product(self, raw_event):
        super().update_product(raw_event)
        if 'features' in raw_event.keys():
            if self._features is None:
                self._features = SmartMeter_ElectricalDataFeatures()
            self._features.update_electrical_data_feature(raw_event['features'])

    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

class Gateway(SunologyAbstractDevice):
    """Home Assistant representation of a Sunology device PLAYMax."""

    def __init__(self, raw_gateway, set_openNetwork_callback: Callable[[bool], None] = None, set_flowWorkingMode_callback: Callable[[FlowWorkingModes], None] = None ):
        """Initialize Gateway device."""        
        super().__init__(raw_gateway)
        self._openNetwork = raw_gateway['zbPairingActivated'] if 'zbPairingActivated' in raw_gateway.keys() else False
        self._flowWorkingMode = raw_gateway['flowWorkingMode'] if 'flowWorkingMode' in raw_gateway.keys() else FlowWorkingModes.POWER_OPTIM.name
        
        self._set_openNetwork_callback = set_openNetwork_callback
        self._set_flowWorkingMode_callback = set_flowWorkingMode_callback

    @property
    def suggested_area(self) -> str:
        """Get the suggested_area."""
        return "Linving room"
        
    @property
    def model_name(self) -> str:
        """Get the model name."""
        name = "STREAM Connect"
        return name

    @property
    def open_network(self) -> bool:
        """Get the open network status."""
        return self._openNetwork
    
    @open_network.setter
    def open_network(self, open_network: bool):
        """Set the open network status."""
        self._openNetwork = open_network
    
    @property
    def flow_working_mode(self) -> FlowWorkingModes:
        """Get the open network status."""
        return self._flowWorkingMode
    
    @flow_working_mode.setter
    def flow_working_mode(self, flowWorkingMode: FlowWorkingModes):
        """Set the open network status."""
        self._flowWorkingMode = flowWorkingMode


    async def set_openNetwork(self, value: bool):
        if self._set_openNetwork_callback == None:
            LOGGER.error("No callback set for set_openNetwork")
            return
        await self._set_openNetwork_callback(value)

    async def _set_flowWorkingMode(self, value: FlowWorkingModes):
        if self._set_flowWorkingMode_callback == None:
            LOGGER.error("No callback set for set_flowWorkingMode")
            return
        await self._set_flowWorkingMode_callback(value)

    @property
    def device_info(self):
        dev_info = super().device_info
        return dev_info

    def __str__(self) -> str:
        """Get string representation."""
        return f"Sunology Device: {self.name}::{self.model_name}::{self.unique_id}"

    
    def update_product(self, raw_event):
        super().update_product(raw_event)
        if 'zbPairingActivated' in raw_event.keys():
            self._openNetwork = raw_event['zbPairingActivated']
        if 'flowWorkingMode' in raw_event.keys():
            self._flowWorkingMode = raw_event['flowWorkingMode']