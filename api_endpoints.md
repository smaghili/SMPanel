# 3x-ui API Endpoints

Based on the Postman collection at https://www.postman.com/hsanaei/3x-ui/example/5146551-3e2665e8-dad3-441c-9540-892b85a7d546

## Authentication

### Login
- **Endpoint**: `POST /login`
- **Description**: Authenticate and get session token
- **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "password"
  }
  ```

## Panel Management

### Get Panel Info
- **Endpoint**: `GET /panel/status`
- **Description**: Get panel status including CPU, memory, network usage

### Get X-UI Version
- **Endpoint**: `GET /panel/version`
- **Description**: Get the current X-UI version

## Inbound Management

### List Inbounds
- **Endpoint**: `GET /panel/inbounds/list`
- **Description**: Get all inbounds configured on the panel

### Add Inbound
- **Endpoint**: `POST /panel/inbound/add`
- **Description**: Add a new inbound configuration

### Update Inbound
- **Endpoint**: `POST /panel/inbound/update/{id}`
- **Description**: Update an existing inbound configuration

### Delete Inbound
- **Endpoint**: `POST /panel/inbound/del/{id}`
- **Description**: Delete an inbound configuration

## Client Management

### Add Client
- **Endpoint**: `POST /panel/inbound/addClient`
- **Description**: Add a client to an inbound
- **Request Body**:
  ```json
  {
    "id": 1,
    "settings": {
      "clients": [
        {
          "email": "new_client@example.com",
          "uuid": "auto-generated-if-empty",
          "enable": true,
          "flow": "",
          "limitIp": 0,
          "totalGB": 0,
          "expiryTime": 0
        }
      ]
    }
  }
  ```

### Update Client
- **Endpoint**: `POST /panel/inbound/updateClient/{email}`
- **Description**: Update an existing client configuration

### Delete Client
- **Endpoint**: `POST /panel/inbound/delClient/{email}`
- **Description**: Delete a client

## Traffic Statistics

### Get Traffic Statistics
- **Endpoint**: `GET /panel/inbounds/getClientTraffics/{email}`
- **Description**: Get traffic usage for a specific client

### Reset Traffic Statistics
- **Endpoint**: `POST /panel/inbound/resetClientTraffic/{email}`
- **Description**: Reset traffic statistics for a client

## Subscription Management

### Get Subscription URL
- **Endpoint**: `GET /sub/{subid}`
- **Description**: Generate subscription URL for clients

## System Management

### Restart X-UI
- **Endpoint**: `POST /panel/setting/restartPanel`
- **Description**: Restart the X-UI panel 