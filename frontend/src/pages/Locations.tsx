// Copyright (c) 2024 RackPlane <info@rackplane.com>
// Version: 1.0.0


import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../config/api';
import { useAuth } from '../contexts/AuthContext';
import { useWhiteLabel } from '../contexts/WhiteLabelContext';
import logger from '../utils/logger';

// Helper function to format API errors
const formatError = (error: any): string => {
  if (typeof error === 'string') {
    return error;
  }
  if (Array.isArray(error)) {
    return error.map(err => {
      const field = err.loc ? err.loc.join('.') : 'unknown';
      return `${field}: ${err.msg}`;
    }).join('; ');
  }
  if (typeof error === 'object' && error.msg) {
    return error.msg;
  }
  return 'An error occurred';
};

interface Datacenter {
  id: number;
  name: string;
  code: string;
  city?: string;
  address?: string;
  total_power_capacity_kw?: number;
  total_cooling_capacity_btu?: number;
}

interface Rack {
  id: number;
  datacenter_id: number;
  room_id?: number;
  name: string;
  code: string;
  height_u: number;
  power_capacity_watts?: number;
  row?: string;
  position?: string;
}

interface DatacenterFormData {
  name: string;
  code: string;
  address: string;
  city: string;
  total_power_capacity_kw: string;
  total_cooling_capacity_btu: string;
}

interface RackFormData {
  datacenter_id: string;
  room_id: string;
  name: string;
  code: string;
  height_u: string;
  power_capacity_watts: string;
  row: string;
  position: string;
}

interface Room {
  id: number;
  datacenter_id: number;
  name: string;
  code: string;
  floor_number?: number;
  power_capacity_kw?: number;
  aisle_configuration?: string;
}

interface RoomFormData {
  datacenter_id: string;
  name: string;
  code: string;
  floor_number: string;
  power_capacity_kw: string;
  aisle_configuration: string;
}

interface StorageContainer {
  id: number;
  name: string;
  container_type: string;
  datacenter_id?: number;
  room_id?: number;
  location?: string;
  description?: string;
  barcode?: string;
}

const Locations: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { t } = useWhiteLabel();
  const [datacenters, setDatacenters] = useState<Datacenter[]>([]);
  const [racks, setRacks] = useState<Rack[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [allRooms, setAllRooms] = useState<Room[]>([]); // Store all rooms for total count
  const [selectedDC, setSelectedDC] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'datacenters' | 'rooms' | 'racks'>('datacenters');

  // Datacenter modal state
  const [showDCModal, setShowDCModal] = useState(false);
  const [editingDC, setEditingDC] = useState<Datacenter | null>(null);
  const [dcFormData, setDCFormData] = useState<DatacenterFormData>({
    name: '',
    code: '',
    address: '',
    city: '',
    total_power_capacity_kw: '',
    total_cooling_capacity_btu: '',
  });

  // Rack modal state
  const [showRackModal, setShowRackModal] = useState(false);
  const [editingRack, setEditingRack] = useState<Rack | null>(null);
  const [rackFormData, setRackFormData] = useState<RackFormData>({
    datacenter_id: '',
    room_id: '',
    name: '',
    code: '',
    height_u: '42',
    power_capacity_watts: '',
    row: '',
    position: '',
  });

  // Room modal state
  const [showRoomModal, setShowRoomModal] = useState(false);
  const [editingRoom, setEditingRoom] = useState<Room | null>(null);
  const [roomFormData, setRoomFormData] = useState<RoomFormData>({
    datacenter_id: '',
    name: '',
    code: '',
    floor_number: '',
    power_capacity_kw: '',
    aisle_configuration: '',
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDatacenters();
    fetchAllRooms(); // Fetch all rooms for total count
  }, []);

  useEffect(() => {
    if (selectedDC) {
      if (activeTab === 'racks') {
        fetchRacks(selectedDC);
      }
      fetchRooms(selectedDC);
    } else {
      // If no datacenter selected (or "All" selected), fetch all
      if (activeTab === 'racks') {
        fetchAllRacks();
      }
      fetchAllRooms();
    }
  }, [selectedDC, activeTab]);

  const fetchDatacenters = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters`);
      setDatacenters(response.data || []);
      // Don't auto-select first datacenter - let user choose "All" or specific datacenter
    } catch (error) {
      logger.error('Error fetching datacenters:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRooms = async (dcId: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/datacenters/${dcId}/rooms`);
      setRooms(response.data || []);
    } catch (error) {
      logger.error('Error fetching rooms:', error);
    }
  };

  const fetchAllRooms = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/rooms`);
      const allRoomsData = response.data || [];
      setAllRooms(allRoomsData);
      setRooms(allRoomsData); // Show all rooms when fetching all
    } catch (error) {
      logger.error('Error fetching all rooms:', error);
    }
  };

  const fetchAllRacks = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks`);
      setRacks(response.data || []);
    } catch (error) {
      logger.error('Error fetching all racks:', error);
    }
  };

  const fetchRacks = async (dcId: number) => {
    try {
      const response = await axios.get(`${API_URL}/api/v1/locations/racks?datacenter_id=${dcId}`);
      setRacks(response.data || []);
    } catch (error) {
      logger.error('Error fetching racks:', error);
    }
  };


  // Datacenter CRUD operations
  const openAddDCModal = () => {
    setEditingDC(null);
    setDCFormData({
      name: '',
      code: '',
      address: '',
      city: '',
      total_power_capacity_kw: '',
      total_cooling_capacity_btu: '',
    });
    setError(null);
    setShowDCModal(true);
  };

  const openEditDCModal = (dc: Datacenter) => {
    setEditingDC(dc);
    setDCFormData({
      name: dc.name,
      code: dc.code,
      address: dc.address || '',
      city: dc.city || '',
      total_power_capacity_kw: dc.total_power_capacity_kw?.toString() || '',
      total_cooling_capacity_btu: dc.total_cooling_capacity_btu?.toString() || '',
    });
    setError(null);
    setShowDCModal(true);
  };

  const closeDCModal = () => {
    setShowDCModal(false);
    setEditingDC(null);
    setError(null);
  };

  const handleDCInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setDCFormData({
      ...dcFormData,
      [e.target.name]: e.target.value,
    });
  };

  const handleDCSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        name: dcFormData.name,
        code: dcFormData.code,
        address: dcFormData.address || null,
        city: dcFormData.city || null,
        total_power_capacity_kw: dcFormData.total_power_capacity_kw ? parseFloat(dcFormData.total_power_capacity_kw) : null,
        total_cooling_capacity_btu: dcFormData.total_cooling_capacity_btu ? parseFloat(dcFormData.total_cooling_capacity_btu) : null,
      };

      if (editingDC) {
        await axios.put(`${API_URL}/api/v1/locations/datacenters/${editingDC.id}`, payload);
      } else {
        await axios.post(`${API_URL}/api/v1/locations/datacenters`, payload);
      }

      await fetchDatacenters();
      closeDCModal();
    } catch (err: any) {
      logger.error('Error saving datacenter:', err);
      const errorDetail = err.response?.data?.detail || 'Failed to save datacenter';
      setError(formatError(errorDetail));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteDC = async (dcId: number) => {
    if (!window.confirm('Are you sure you want to delete this datacenter?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/v1/locations/datacenters/${dcId}`);
      await fetchDatacenters();
      if (selectedDC === dcId) {
        setSelectedDC(null);
      }
    } catch (err: any) {
      logger.error('Error deleting datacenter:', err);
      alert(err.response?.data?.detail || 'Failed to delete datacenter');
    }
  };

  // Rack CRUD operations
  const openAddRackModal = () => {
    setEditingRack(null);
    setRackFormData({
      datacenter_id: selectedDC?.toString() || '',
      room_id: '',
      name: '',
      code: '',
      height_u: '42',
      power_capacity_watts: '',
      row: '',
      position: '',
    });
    setError(null);
    setShowRackModal(true);
  };

  const openEditRackModal = (rack: Rack) => {
    setEditingRack(rack);
    setRackFormData({
      datacenter_id: rack.datacenter_id.toString(),
      room_id: rack.room_id?.toString() || '',
      name: rack.name,
      code: rack.code,
      height_u: rack.height_u.toString(),
      power_capacity_watts: rack.power_capacity_watts?.toString() || '',
      row: rack.row || '',
      position: rack.position || '',
    });
    setError(null);
    setShowRackModal(true);
  };

  const closeRackModal = () => {
    setShowRackModal(false);
    setEditingRack(null);
    setError(null);
  };

  const handleRackInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setRackFormData({
      ...rackFormData,
      [e.target.name]: e.target.value,
    });
  };

  const handleRackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        datacenter_id: parseInt(rackFormData.datacenter_id),
        room_id: rackFormData.room_id ? parseInt(rackFormData.room_id) : null,
        name: rackFormData.name,
        code: rackFormData.code,
        height_u: parseInt(rackFormData.height_u),
        power_capacity_watts: rackFormData.power_capacity_watts ? parseFloat(rackFormData.power_capacity_watts) : null,
        row: rackFormData.row || null,
        position: rackFormData.position || null,
      };

      if (editingRack) {
        await axios.put(`${API_URL}/api/v1/locations/racks/${editingRack.id}`, payload);
      } else {
        await axios.post(`${API_URL}/api/v1/locations/racks`, payload);
      }

      if (selectedDC) {
        await fetchRacks(selectedDC);
      }
      closeRackModal();
    } catch (err: any) {
      logger.error('Error saving rack:', err);
      const errorDetail = err.response?.data?.detail || 'Failed to save rack';
      setError(formatError(errorDetail));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRack = async (rackId: number) => {
    if (!window.confirm('Are you sure you want to delete this rack?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/v1/locations/racks/${rackId}`);
      if (selectedDC) {
        await fetchRacks(selectedDC);
      }
    } catch (err: any) {
      logger.error('Error deleting rack:', err);
      alert(err.response?.data?.detail || 'Failed to delete rack');
    }
  };

  // Room CRUD operations
  const openAddRoomModal = () => {
    setEditingRoom(null);
    setRoomFormData({
      datacenter_id: selectedDC?.toString() || '',
      name: '',
      code: '',
      floor_number: '',
      power_capacity_kw: '',
      aisle_configuration: '',
    });
    setError(null);
    setShowRoomModal(true);
  };

  const openEditRoomModal = (room: Room) => {
    setEditingRoom(room);
    setRoomFormData({
      datacenter_id: room.datacenter_id.toString(),
      name: room.name,
      code: room.code,
      floor_number: room.floor_number?.toString() || '',
      power_capacity_kw: room.power_capacity_kw?.toString() || '',
      aisle_configuration: room.aisle_configuration || '',
    });
    setError(null);
    setShowRoomModal(true);
  };

  const closeRoomModal = () => {
    setShowRoomModal(false);
    setEditingRoom(null);
    setError(null);
  };

  const handleRoomInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setRoomFormData({
      ...roomFormData,
      [e.target.name]: e.target.value,
    });
  };

  const handleRoomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const payload: any = {
        datacenter_id: parseInt(roomFormData.datacenter_id),
        name: roomFormData.name,
        code: roomFormData.code,
        floor_number: roomFormData.floor_number ? parseInt(roomFormData.floor_number) : null,
        power_capacity_kw: roomFormData.power_capacity_kw ? parseFloat(roomFormData.power_capacity_kw) : null,
        aisle_configuration: roomFormData.aisle_configuration || null,
      };

      if (editingRoom) {
        await axios.put(`${API_URL}/api/v1/locations/rooms/${editingRoom.id}`, payload);
      } else {
        await axios.post(`${API_URL}/api/v1/locations/rooms`, payload);
      }

      if (selectedDC) {
        await fetchRooms(selectedDC);
      }
      closeRoomModal();
    } catch (err: any) {
      logger.error('Error saving room:', err);
      const errorDetail = err.response?.data?.detail || 'Failed to save room';
      setError(formatError(errorDetail));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRoom = async (roomId: number) => {
    if (!window.confirm('Are you sure you want to delete this room?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/v1/locations/rooms/${roomId}`);
      if (selectedDC) {
        await fetchRooms(selectedDC);
      }
    } catch (err: any) {
      logger.error('Error deleting room:', err);
      alert(err.response?.data?.detail || 'Failed to delete room');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-gray-500 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-primary">{t('locations')} & {t('bins')}</h1>
        <div className="space-x-2">
          {isAuthenticated && (
            <>
              <button onClick={openAddDCModal} className="btn-primary">+ Add {t('location')}</button>
              {selectedDC && <button onClick={openAddRackModal} className="btn-primary">+ Add {t('bin')}</button>}
            </>
          )}
          {!isAuthenticated && (
            <p className="text-sm text-gray-500 dark:text-gray-400 italic">Login to make changes</p>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b" style={{ borderColor: 'var(--border-color)' }}>
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('datacenters')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'datacenters'
              ? 'text-primary'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-primary'
              }`}
            style={activeTab === 'datacenters' ? { borderColor: 'var(--primary)' } : { borderColor: 'transparent' }}
          >
            {t('locations')} ({datacenters.length})
          </button>
          <button
            onClick={() => setActiveTab('rooms')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'rooms'
              ? 'text-primary'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-primary'
              }`}
            style={activeTab === 'rooms' ? { borderColor: 'var(--primary)' } : { borderColor: 'transparent' }}
          >
            Rooms ({allRooms.length})
          </button>
          <button
            onClick={() => setActiveTab('racks')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${activeTab === 'racks'
              ? 'text-primary'
              : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-primary'
              }`}
            style={activeTab === 'racks' ? { borderColor: 'var(--primary)' } : { borderColor: 'transparent' }}
          >
            {t('bins')} ({racks.length})
          </button>
        </nav>
      </div>

      {/* Datacenters Tab */}
      {activeTab === 'datacenters' && (
        <div className="card">
          <h2 className="text-xl font-bold text-primary mb-4">{t('locations')}</h2>
          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Code</th>
                  <th>City</th>
                  <th>Power (kW)</th>
                  <th>Cooling (BTU)</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {datacenters.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-gray-500 dark:text-gray-400">
                      No {t('locations').toLowerCase()} found
                    </td>
                  </tr>
                ) : (
                  datacenters.map((dc) => (
                    <tr key={dc.id} style={selectedDC === dc.id ? { backgroundColor: 'rgba(0, 123, 255, 0.1)' } : {}}>
                      <td className="font-medium text-primary">{dc.name}</td>
                      <td className="text-primary">{dc.code}</td>
                      <td className="text-primary">{dc.city || '-'}</td>
                      <td className="text-primary">{dc.total_power_capacity_kw || '-'}</td>
                      <td className="text-primary">{dc.total_cooling_capacity_btu || '-'}</td>
                      <td>
                        <button
                          onClick={() => setSelectedDC(dc.id)}
                          className="mr-3"
                          style={{ color: 'var(--primary)' }}
                        >
                          Select
                        </button>
                        {isAuthenticated && (
                          <>
                            <button
                              onClick={() => openEditDCModal(dc)}
                              className="mr-3"
                              style={{ color: 'var(--success)' }}
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteDC(dc.id)}
                              style={{ color: 'var(--danger)' }}
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rooms Tab */}
      {activeTab === 'rooms' && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-4">
              <h2 className="text-xl font-bold text-primary">
                Rooms {selectedDC && `in ${datacenters.find(dc => dc.id === selectedDC)?.name}`}
              </h2>
              {datacenters.length > 0 && (
                <select
                  value={selectedDC || ''}
                  onChange={(e) => {
                    const dcId = e.target.value ? parseInt(e.target.value) : null;
                    setSelectedDC(dcId);
                  }}
                  className="input"
                >
                  <option value="">All {t('locations')}</option>
                  {datacenters.map(dc => (
                    <option key={dc.id} value={dc.id}>
                      {dc.name} ({dc.code})
                    </option>
                  ))}
                </select>
              )}
            </div>
            {isAuthenticated && selectedDC && (
              <button onClick={openAddRoomModal} className="btn-primary">
                + Add Room
              </button>
            )}
            {!selectedDC && (
              <p className="text-sm text-gray-500 dark:text-gray-400">Select a {t('location').toLowerCase()} to view its rooms</p>
            )}
          </div>

          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  {!selectedDC && <th>{t('location')}</th>}
                  <th>Floor</th>
                  <th>Power (kW)</th>
                  <th>Aisle Config</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rooms.length === 0 ? (
                  <tr>
                    <td colSpan={selectedDC ? 6 : 7} className="text-center py-8 text-gray-500 dark:text-gray-400">
                      {selectedDC ? `No rooms found in this ${t('location').toLowerCase()}` : 'No rooms found'}
                    </td>
                  </tr>
                ) : (
                  rooms.map((room) => {
                    const roomDatacenter = datacenters.find(dc => dc.id === room.datacenter_id);
                    return (
                      <tr key={room.id}>
                        <td className="font-medium text-primary">{room.code}</td>
                        <td className="text-primary">{room.name}</td>
                        {!selectedDC && (
                          <td className="text-primary">{roomDatacenter ? roomDatacenter.name : '-'}</td>
                        )}
                        <td className="text-primary">{room.floor_number !== undefined && room.floor_number !== null ? `Floor ${room.floor_number}` : '-'}</td>
                        <td className="text-primary">{room.power_capacity_kw ? `${room.power_capacity_kw} kW` : '-'}</td>
                        <td className="text-primary">{room.aisle_configuration || '-'}</td>
                        <td>
                          {isAuthenticated && (
                            <>
                              <button
                                onClick={() => openEditRoomModal(room)}
                                className="mr-3"
                                style={{ color: 'var(--success)' }}
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteRoom(room.id)}
                                style={{ color: 'var(--danger)' }}
                              >
                                Delete
                              </button>
                            </>
                          )}
                          {!isAuthenticated && (
                            <span className="text-gray-500 dark:text-gray-400 text-sm">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Racks Tab - Unified across all verticals, terminology handles display names */}
      {activeTab === 'racks' && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <div className="flex items-center gap-4">
              <h2 className="text-xl font-bold text-primary">
                {t('bins')} {selectedDC && `in ${datacenters.find(dc => dc.id === selectedDC)?.name}`}
              </h2>
              {datacenters.length > 0 && (
                <select
                  value={selectedDC || ''}
                  onChange={(e) => {
                    const dcId = e.target.value ? parseInt(e.target.value) : null;
                    setSelectedDC(dcId);
                  }}
                  className="input"
                >
                  <option value="">All {t('locations')}</option>
                  {datacenters.map(dc => (
                    <option key={dc.id} value={dc.id}>
                      {dc.name} ({dc.code})
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Name</th>
                  {!selectedDC && <th>{t('location')}</th>}
                  <th>Room</th>
                  <th>Height (U)</th>
                  <th>Power (W)</th>
                  <th>Row</th>
                  <th>Position</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {racks.length === 0 ? (
                  <tr>
                    <td colSpan={selectedDC ? 8 : 9} className="text-center py-8 text-gray-500 dark:text-gray-400">
                      {selectedDC ? `No ${t('bins').toLowerCase()} found in this ${t('location').toLowerCase()}` : `No ${t('bins').toLowerCase()} found`}
                    </td>
                  </tr>
                ) : (
                  racks.map((rack) => {
                    const rackDatacenter = datacenters.find(dc => dc.id === rack.datacenter_id);
                    return (
                      <tr key={rack.id}>
                        <td className="font-medium text-primary">{rack.code}</td>
                        <td className="text-primary">{rack.name}</td>
                        {!selectedDC && (
                          <td className="text-primary">{rackDatacenter ? rackDatacenter.name : '-'}</td>
                        )}
                        <td className="text-primary">{rack.room_id ? rooms.find(r => r.id === rack.room_id)?.name || '-' : '-'}</td>
                        <td className="text-primary">{rack.height_u}U</td>
                        <td className="text-primary">{rack.power_capacity_watts ? `${(rack.power_capacity_watts / 1000).toFixed(1)} kW` : '-'}</td>
                        <td className="text-primary">{rack.row || '-'}</td>
                        <td className="text-primary">{rack.position || '-'}</td>
                        <td>
                          {isAuthenticated && (
                            <>
                              <button
                                onClick={() => navigate(`/racks/${rack.id}`)}
                                className="mr-3"
                                style={{ color: 'var(--primary)' }}
                                title={`View ${t('bin')} Visualization`}
                              >
                                View
                              </button>
                              <button
                                onClick={() => openEditRackModal(rack)}
                                className="mr-3"
                                style={{ color: 'var(--success)' }}
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => handleDeleteRack(rack.id)}
                                style={{ color: 'var(--danger)' }}
                              >
                                Delete
                              </button>
                            </>
                          )}
                          {!isAuthenticated && (
                            <span className="text-gray-500 dark:text-gray-400 text-sm">-</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Datacenter Modal - Continued in next message due to length */}
      {showDCModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-primary">
                  {editingDC ? `Edit ${t('location')}` : `Add New ${t('location')}`}
                </h2>
                <button
                  onClick={closeDCModal}
                  className="text-gray-500 dark:text-gray-400 hover:text-primary text-2xl"
                >
                  &times;
                </button>
              </div>

              {error && (
                <div className="mb-4 p-3 border rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: 'var(--danger)' }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleDCSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Name <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={dcFormData.name}
                      onChange={handleDCInputChange}
                      required
                      className="input w-full"
                      placeholder={`Main ${t('location')}`}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Code <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="text"
                      name="code"
                      value={dcFormData.code}
                      onChange={handleDCInputChange}
                      required
                      className="input w-full"
                      placeholder="DC01"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      City
                    </label>
                    <input
                      type="text"
                      name="city"
                      value={dcFormData.city}
                      onChange={handleDCInputChange}
                      className="input w-full"
                      placeholder="New York"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Address
                    </label>
                    <input
                      type="text"
                      name="address"
                      value={dcFormData.address}
                      onChange={handleDCInputChange}
                      className="input w-full"
                      placeholder="123 Main St"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Power Capacity (kW)
                    </label>
                    <input
                      type="number"
                      name="total_power_capacity_kw"
                      value={dcFormData.total_power_capacity_kw}
                      onChange={handleDCInputChange}
                      min="0"
                      step="0.01"
                      className="input w-full"
                      placeholder="1000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Cooling Capacity (BTU)
                    </label>
                    <input
                      type="number"
                      name="total_cooling_capacity_btu"
                      value={dcFormData.total_cooling_capacity_btu}
                      onChange={handleDCInputChange}
                      min="0"
                      step="0.01"
                      className="input w-full"
                      placeholder="50000"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6">
                  <button
                    type="button"
                    onClick={closeDCModal}
                    className="btn-secondary"
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : editingDC ? `Update ${t('location')}` : `Create ${t('location')}`}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Rack Modal */}
      {showRackModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-primary">
                  {editingRack ? `Edit ${t('bin')}` : `Add New ${t('bin')}`}
                </h2>
                <button
                  onClick={closeRackModal}
                  className="text-gray-500 dark:text-gray-400 hover:text-primary text-2xl"
                >
                  &times;
                </button>
              </div>

              {error && (
                <div className="mb-4 p-3 border rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: 'var(--danger)' }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleRackSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('location')} <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <select
                      name="datacenter_id"
                      value={rackFormData.datacenter_id}
                      onChange={handleRackInputChange}
                      required
                      className="input w-full"
                    >
                      <option value="">Select a {t('location').toLowerCase()}...</option>
                      {datacenters.map(dc => (
                        <option key={dc.id} value={dc.id}>
                          {dc.name} ({dc.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Room
                    </label>
                    <select
                      name="room_id"
                      value={rackFormData.room_id}
                      onChange={handleRackInputChange}
                      className="input w-full"
                      disabled={!rackFormData.datacenter_id}
                    >
                      <option value="">-- Select Room --</option>
                      {rooms
                        .filter(room => !rackFormData.datacenter_id || room.datacenter_id === parseInt(rackFormData.datacenter_id))
                        .map(room => (
                          <option key={room.id} value={room.id}>
                            {room.name} ({room.code})
                          </option>
                        ))}
                    </select>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {!rackFormData.datacenter_id ? `Select a ${t('location').toLowerCase()} first` : `Optional - Select specific room for this ${t('bin').toLowerCase()}`}
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Name <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={rackFormData.name}
                      onChange={handleRackInputChange}
                      required
                      className="input w-full"
                      placeholder={`${t('bin')} A1`}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Code <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="text"
                      name="code"
                      value={rackFormData.code}
                      onChange={handleRackInputChange}
                      required
                      className="input w-full"
                      placeholder="R01-A-01"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Height (U) <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="number"
                      name="height_u"
                      value={rackFormData.height_u}
                      onChange={handleRackInputChange}
                      required
                      min="1"
                      max="52"
                      className="input w-full"
                      placeholder="42"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Power Capacity (Watts)
                    </label>
                    <input
                      type="number"
                      name="power_capacity_watts"
                      value={rackFormData.power_capacity_watts}
                      onChange={handleRackInputChange}
                      min="0"
                      step="0.01"
                      className="input w-full"
                      placeholder="5000"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Row
                    </label>
                    <input
                      type="text"
                      name="row"
                      value={rackFormData.row}
                      onChange={handleRackInputChange}
                      className="input w-full"
                      placeholder="A"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Position
                    </label>
                    <input
                      type="text"
                      name="position"
                      value={rackFormData.position}
                      onChange={handleRackInputChange}
                      className="input w-full"
                      placeholder="01"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6">
                  <button
                    type="button"
                    onClick={closeRackModal}
                    className="btn-secondary"
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : editingRack ? `Update ${t('bin')}` : `Create ${t('bin')}`}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Room Modal */}
      {showRoomModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
            <div className="p-6">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-primary">
                  {editingRoom ? 'Edit Room' : 'Add New Room'}
                </h2>
                <button
                  onClick={closeRoomModal}
                  className="text-secondary hover:text-primary text-2xl"
                >
                  &times;
                </button>
              </div>

              {error && (
                <div className="mb-4 p-3 border rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.3)', color: 'var(--danger)' }}>
                  {error}
                </div>
              )}

              <form onSubmit={handleRoomSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      {t('location')} <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <select
                      name="datacenter_id"
                      value={roomFormData.datacenter_id}
                      onChange={handleRoomInputChange}
                      required
                      className="input w-full"
                    >
                      <option value="">Select a {t('location').toLowerCase()}...</option>
                      {datacenters.map(dc => (
                        <option key={dc.id} value={dc.id}>
                          {dc.name} ({dc.code})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Name <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={roomFormData.name}
                      onChange={handleRoomInputChange}
                      required
                      className="input w-full"
                      placeholder="Server Room A"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Code <span style={{ color: 'var(--danger)' }}>*</span>
                    </label>
                    <input
                      type="text"
                      name="code"
                      value={roomFormData.code}
                      onChange={handleRoomInputChange}
                      required
                      className="input w-full"
                      placeholder="SRA"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Floor Number
                    </label>
                    <input
                      type="number"
                      name="floor_number"
                      value={roomFormData.floor_number}
                      onChange={handleRoomInputChange}
                      min="0"
                      className="input w-full"
                      placeholder="1"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-primary mb-2">
                      Power Capacity (kW)
                    </label>
                    <input
                      type="number"
                      name="power_capacity_kw"
                      value={roomFormData.power_capacity_kw}
                      onChange={handleRoomInputChange}
                      min="0"
                      step="0.01"
                      className="input w-full"
                      placeholder="50.0"
                    />
                  </div>

                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-primary mb-2">
                      Aisle Configuration
                    </label>
                    <input
                      type="text"
                      name="aisle_configuration"
                      value={roomFormData.aisle_configuration}
                      onChange={handleRoomInputChange}
                      className="input w-full"
                      placeholder="e.g., Hot/Cold Aisle"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-3 mt-6">
                  <button
                    type="button"
                    onClick={closeRoomModal}
                    className="btn-secondary"
                    disabled={saving}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : editingRoom ? 'Update Room' : 'Create Room'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Locations;
