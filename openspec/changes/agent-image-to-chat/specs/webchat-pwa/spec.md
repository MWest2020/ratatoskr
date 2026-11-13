## ADDED Requirements

### Requirement: An image in a message shows inline and opens full size

When a message carries an image (an `imeta` tag of type PNG, JPEG or WebP), the
chat SHALL show the image under the message text in the thread. A tap SHALL
open it full screen inside the app, and a tap, Escape or Back SHALL close that
view without leaving the app. Text from the message SHALL enter the page only
as text, never as markup. When the image cannot be shown, the thread SHALL say
why (expired, offline, or the relay error) instead of showing an empty or
broken image.

#### Scenario: Mark opens a thread with a chart

- **WHEN** an agent has sent an image with a caption and Mark opens that
  channel in the installed PWA
- **THEN** the caption and the image are visible in the thread, and a tap shows
  the image full screen

#### Scenario: The image has expired

- **WHEN** the image of a message has been pruned
- **THEN** the message text is still shown, with "image expired (kept 30 days)"
  where the image was

#### Scenario: A re-render does not refetch

- **WHEN** a new message arrives in a channel that already shows an image
- **THEN** the shown image is not fetched again from the server

### Requirement: Images are served only behind the session and only as images

`GET /api/media/<sha256>` SHALL require the same session as the other `/api/`
reads. It SHALL fetch the blob from the relay under the chat's own key, and
SHALL serve it only when its magic bytes are PNG, JPEG or WebP. The
Content-Type SHALL be the type from the magic bytes, and the response SHALL
carry `X-Content-Type-Options: nosniff`, a `default-src 'none'; sandbox`
Content-Security-Policy and `Cache-Control: no-store`. A blob the relay no
longer has SHALL give 410 with a reason, and any other relay failure SHALL give
502 with the reason.

#### Scenario: No session

- **WHEN** a request for `/api/media/<sha256>` arrives without a valid session
- **THEN** it is refused with 401 and the relay is not asked

#### Scenario: A blob that is not an image

- **WHEN** the requested blob holds HTML or SVG
- **THEN** the chat refuses with 415 and serves none of its bytes

### Requirement: A notification for an image message says it carries an image

A push for a message that carries an image SHALL read `🖼 <caption>`, without
any media URL, and a tap SHALL open the message's channel. The push payload
SHALL carry no image bytes.

#### Scenario: Agent sends a screenshot while the app is closed

- **WHEN** an agent sends an image with the caption "login page after deploy"
- **THEN** the phone shows a notification `🖼 login page after deploy`, and a
  tap opens that channel with the image inline
