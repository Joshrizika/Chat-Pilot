import Contacts
import Foundation

let store = CNContactStore()
let keysToFetch = [CNContactGivenNameKey, CNContactFamilyNameKey, CNContactPhoneNumbersKey] as [CNKeyDescriptor]

var contactsArray = [(String, String, String)]() // Array to store given name, family name, and phone number

// Function to clean phone numbers using regex
func cleanPhoneNumber(_ number: String) -> String {
    let regex = try! NSRegularExpression(pattern: "[^0-9+]", options: [])
    let range = NSRange(location: 0, length: number.count)
    return regex.stringByReplacingMatches(in: number, options: [], range: range, withTemplate: "")
}

store.requestAccess(for: .contacts) { granted, error in
    guard granted else {
        print("Access to contacts was denied.")
        exit(1)
    }

    let fetchRequest = CNContactFetchRequest(keysToFetch: keysToFetch)
    try? store.enumerateContacts(with: fetchRequest) { contact, stop in
        let givenName = contact.givenName
        let familyName = contact.familyName

        if let mobilePhoneNumber = contact.phoneNumbers.first(where: { $0.label == CNLabelPhoneNumberMobile })?.value.stringValue {
            contactsArray.append((givenName, familyName, cleanPhoneNumber(mobilePhoneNumber)))
        }
    }

    var contactsDict = [String: String]()
    for (givenName, familyName, phoneNumber) in contactsArray {
        let fullName = "\(givenName) \(familyName)".trimmingCharacters(in: .whitespacesAndNewlines)
        contactsDict[fullName] = phoneNumber
    }

    if let jsonData = try? JSONSerialization.data(withJSONObject: contactsDict, options: .prettyPrinted) {
        let jsonString = String(data: jsonData, encoding: .utf8)
        print(jsonString ?? "")
    }

    exit(0)
}

RunLoop.main.run()
