# CarPlay entitlement request (DRAFT, not submitted)

Submit at https://developer.apple.com/contact/carplay/ while signed in to the Apple Developer account
(maxgreenwald.assistant@gmail.com). Requires the developer account to be active (ID review finished).
Entitlement requested: **CarPlay Navigation app** (`com.apple.developer.carplay-maps`).

| Field | Answer |
|---|---|
| App name | Golf Cart Maps |
| Bundle ID | com.matchimus.golfcartmaps |
| App Store status | In development, TestFlight first; not yet on the App Store |
| Website | https://golfcartmap.com |
| Category requested | Navigation |
| Countries | United States |

## App description
Golf Cart Maps is a navigation app for drivers of street-legal golf carts and low-speed vehicles (LSVs).
These vehicles are legally limited to certain roads: in California an LSV may only use roads posted 35 mph
or less (CVC 21260), and in Florida, Georgia and South Carolina golf carts may only use roads a city or county
has designated, or roads under a set speed limit. Regular navigation apps route these drivers onto roads where
their vehicle is illegal and unsafe. Golf Cart Maps classifies every road in each supported community
(coastal San Diego, The Villages FL, Peachtree City GA, with more planned) using OpenStreetMap speed data,
posted-sign imagery and local ordinances, and plans turn-by-turn routes that only use roads that are legal for
the selected vehicle type (golf cart or LSV), including legal crossings of faster roads. Each trip also shows
the round-trip distance and whether it fits the vehicle's battery range.

## Why the Navigation category
The core function of the app is turn-by-turn route guidance to a destination. On CarPlay it shows a map
(CPMapTemplate) with the legal and off-limits roads highlighted, lets the driver pick a destination by search
or from recent places, shows a trip preview with distance, time and battery range, and then provides
maneuver-by-maneuver guidance (CPNavigationSession / CPManeuver) as they drive. It does not play media,
show video, or offer messaging. It is the same kind of experience as other navigation apps, but with
routing restricted to roads that are legal for low-speed vehicles.

## Target users
- Owners and renters of street-legal golf carts and LSVs in golf cart communities (The Villages FL,
  Peachtree City GA, beach towns in Southern California, and similar communities).
- Golf cart rental companies and dealers who want customers to stay on legal roads.
- Many new golf carts and LSVs ship with touchscreens that support Apple CarPlay (for example DACH Apollo,
  Club Car Onward, Evolution D5, Bintelli), so drivers expect to use navigation on the vehicle's display.

## Safety
Routes avoid roads the vehicle is not allowed on, which keeps slow vehicles off fast roads. The CarPlay
interface uses only Apple's templates, has no keyboard text entry while driving beyond the system search
template, and the map is driver-glanceable (green = OK, red = avoid). The app reminds drivers to obey posted
signs and local laws.

## Additional information
- Developer: Max Greenwald (individual account; moving to Matchimus LLC later).
- Contact: maxgreenwald.assistant@gmail.com
- The CarPlay scene is already built and compiles; we'd like the entitlement to test on devices via TestFlight.
