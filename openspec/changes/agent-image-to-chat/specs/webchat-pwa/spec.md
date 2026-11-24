## ADDED Requirements

### Requirement: A notification for an image message says it carries an image

A push for a message that carries an image SHALL read `🖼 <caption>`, without
any media URL, and a tap SHALL open the message's channel. The push payload
SHALL carry no image bytes.

#### Scenario: Agent sends a screenshot while the app is closed

- **WHEN** an agent sends an image with the caption "login page after deploy"
- **THEN** the phone shows a notification `🖼 login page after deploy`, and a
  tap opens that channel
