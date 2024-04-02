import React, {useState, useEffect, useRef} from 'react';
import axios from 'axios';
import useOutsideClick from './useOutsideClick';
import "./SearchBar.css";

export default function SearchBar(props) {

    const [searchTerm, setSearchTerm] = useState("");
    const [modelSuggestions, setModelSuggestions] = useState([]);
    const [partSuggestions, setPartSuggestions] = useState([]);
    const [isLoading, setIsLoading] = useState(null);
    const [manufacturers, setManufacturers] = useState([]);
    const [recommendations, setRecommendations] = useState([]);
    const [error, setError] = useState(null);
    const [custServResponse, setCustServResponse] = useState("");
    const [isDropdownVisible, setIsDropdownVisible] = useState(true);
    const maxQueryLen = 20;
    const searchBarRef = useRef(null);

    const handleSearchChange = (event) => {
        const value = event.target.value;
        setSearchTerm(value);
    };

    const onOutsideClick = () => {
      setIsDropdownVisible(false);
    };

    useOutsideClick(searchBarRef, onOutsideClick);

    useEffect(() => {
        setCustServResponse("");
        if (searchTerm.length < 3 || searchTerm.length >= maxQueryLen) {
          setIsLoading(true);
          setModelSuggestions([]);
          setPartSuggestions([]);
          setManufacturers([]);
          setRecommendations([]);
          setError(null);
          setIsLoading(false);
          return;
        }
        const debounceTimeout = setTimeout(() => {
          setIsLoading(true);
          if (searchTerm && !searchTerm.match(/how to replace.*element.*/) && !searchTerm.match(/how to test.*element.*/)) {
            // setIsLoading(true);
            setError(null);
    
            const source = axios.CancelToken.source();
    
            axios.get(`https://instaagentsearch-mwvqt7kpva-uc.a.run.app/fetch_all?searchTerm=${encodeURIComponent(searchTerm)}`, {
                cancelToken: source.token,
              })
              .then(response => response.data)
              .then(function(response) {
                // console.log(response);
                if (response.parts && response.parts.length !== 0) {
                  setPartSuggestions(response.parts.map((pt) => 
                    pt ? pt.toUpperCase() : ""
                  ))
                }
          
                  if(response.models && response.models.length !== 0){
                    setModelSuggestions(response.models.map((mn) => 
                      mn ? mn.toUpperCase() : ""
                  ))
                }
          
                if(response.manufacturers && response.manufacturers.length!==0) {
                  setManufacturers(response.manufacturers);
                }
          
                if (response.recommendations && response.recommendations.length!==0) {
                  setRecommendations(response.recommendations.slice(0, 5));
                  }     
                 setIsLoading(false);
              })
              .catch(function (error) {
                if (axios.isCancel(error)) {
                  console.log("Request canceled:", error.message);
                } else {
                  console.log(error);
                  setError("Something went wrong");
                  setIsLoading(false);
                }
              })
            return () => {
              source.cancel("Operation canceled by the user.");
            };  
          }
          if (searchTerm.match(/how to test.*element.*/)) {
            
            setError(null);
            setTimeout(() => {
            setIsLoading(false);
            setCustServResponse(`<p style={{
              backgroundColor: 'white',
              padding: '15px',
              borderRadius: '8px',
              margin: '10px 0',
              boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
              fontWeight: 'bold',
            }}
          >
          Disconnect the power source to your dryer before you conduct this or any other test. Either unplug the unit from the wall outlet, remove the appropriate fuse from the fuse box, or flip the appropriate breaker in the circuit breaker panel.
          Disconnect the power source to your dryer before you conduct this or any other test. Either unplug the unit from the wall outlet, remove the appropriate fuse from the fuse box, or flip the appropriate breaker in the circuit breaker panel.
          </p>
          <p>Dryer heating elements come in various shapes and sizes. They are all strung with a coiled wire made of a nickel and a chrome alloy. This wire receives, but resists, a controlled electric current and as a result, the wire heats up. The heat produced is used to dry the clothes in your dryer.</p>
          
          <p>Depending on your model, you may need to disassemble your dryer's cabinet in order to access and replace the heating element. If you have not yet disassembled your dryer to access your heating element, you can learn how to do so by referring to our <a href="https://www.partselect.com/dryer+open-cabinet+repair.htm">How to open your dryer's cabinet section</a>.</p>
          
          <p>Also depending on your model, you may not have to replace the entire heater assembly. You may need to replace only the wire coil. Most dryer heating elements are held in place with just a few screws. Sometimes as few as two. Remove each of the screws retaining the element in order to be able to remove it. Install a new heating element in place of the old one. Secure it in place with the required amount of screws. Reassemble the dryer's cabinet, and restore power to the unit.</p>
          `);
            }, 1800); 
          }
          if (searchTerm.match(/how to replace.*element.*/)) {
            
            setError(null);
            setTimeout(() => {
            setIsLoading(false);
            setCustServResponse(`<p style={{
              backgroundColor: 'white', // String values must be in quotes
              padding: '15px',
              borderRadius: '8px',
              margin: '10px 0',
              boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
              fontWeight: 'bold',
            }}
          >
          Note:
          Disconnect the power source to your dryer before you conduct this or any other test. Either unplug the unit from the wall outlet, remove the appropriate fuse from the fuse box, or flip the appropriate breaker in the circuit breaker panel.
          </p>
          
          <p>Dryer heating elements come in various shapes and sizes. They are all strung with a coiled wire made of a nickel and a chrome alloy. This wire receives, but resists, a controlled electric current and as a result, the wire heats up. The heat produced is used to heat and dry the clothes in your dryer.</p>
          
          <p>Depending on your model, you may need to disassemble your dryer's cabinet in order to access and replace the heating element. If you have not yet disassembled your dryer to access your heating element, you can learn how to do so by referring to our <a href="https://www.partselect.com/dryer+open-cabinet+repair.htm">How to open your dryer's cabinet section</a></p>
          
          <p>Once you have gained access to your dryer's heating element, set your multimeter to the R x 1 resistance scale. Touch each meter probe and to one end of the element. If you receive a reading of infinite resistance, then your heating element is no longer functioning properly and you will have to replace it.`);
            }, 1800); 
          }
        }, 500);
        return () => clearTimeout(debounceTimeout);
      }, [searchTerm]);

    const handleSubmit = (event) => {
        event.preventDefault();
        console.log(`Searching for: ${searchTerm}`);
        setModelSuggestions([]);
        setPartSuggestions([]);
        setManufacturers([]);
        setRecommendations([]);
        props.onSearchHandler(searchTerm);
        setSearchTerm("");
    };
    

    return (
          <div>
          <form onSubmit={handleSubmit} ref={searchBarRef}>
            <input
              type="text"
              placeholder="Search model or part number"
              value={searchTerm}
              onChange={handleSearchChange}
              onFocus={() => setIsDropdownVisible(true)}
              style={{ padding: '10px', paddingRight: '10px' }}
            />
            {searchTerm && (
              <div
                style={{
                  position: 'absolute',
                  top: '50%',
                  right: '12%',
                  transform: 'translateY(-50%)',
                  cursor: 'pointer'
                }}
                onClick={() => handleSearchChange({ target: { value: '' } })}
              >
                &#x2715;
              </div>
            )}
          <div className={props.page==="searchpage"? "button-container-searchpage": "button-container"}>
            <button type="submit">
              {!isLoading ? "Search" : <div className="loader"></div>}
              {error && <div>{error}</div>}
            </button>
          </div>
          </form>
          {(modelSuggestions.length > 0 ||
            partSuggestions.length > 0 ||
            manufacturers.length ||
            recommendations.length > 0) && (isDropdownVisible) && !(searchTerm.match(/how to replace.*element.*/)) && !(searchTerm.match(/how to test.*element.*/)) && (
            <div className="suggestions-dropdown">
              {modelSuggestions.length > 0 && <div className="suggestions-column">
                <h3>Matching Models</h3>
                <ul>
                  {
                    modelSuggestions.map((suggestion, index) => (
                        <li
                          key={index}
                        >
                          <span
                                    dangerouslySetInnerHTML={{
                                      __html: suggestion.replace(
                                        new RegExp(`(${searchTerm})`, "gi"),
                                        "<strong>$1</strong>"
                                      ),
                                    }}
                                  />
                        </li>
                      ))}
                </ul>
              </div>}
              {partSuggestions.length>0 && <div className="suggestions-column">
                <h3>Matching Parts</h3>
                <ul>
                  {
                    partSuggestions.map((suggestion, index) => (
                        <li
                          key={index}
                        >
                          <span
                                    dangerouslySetInnerHTML={{
                                      __html: suggestion.replace(
                                        new RegExp(`(${searchTerm})`, "gi"),
                                        "<strong>$1</strong>"
                                      ),
                                    }}
                                  />
                        </li>
                      ))}
                </ul>
              </div>}
              {manufacturers.length > 0 && <div className="suggestions-column">
                <h3>Manufacturers</h3>
                <ul>
                  {
                  manufacturers.map((manu, index) => {
                    const manufacturerName = Object.keys(manu)[0];
                    const logoUrl = manu[manufacturerName];
                  
                    return (
                      <li
                        key={index}
                      >
                        <div style={{ display: "flex", paddingTop: "8px", alignItems: "center" }}>
                          <div style={{ marginRight: "20px" }}>
                            <img
                              src={logoUrl}
                              alt={`${manufacturerName} Logo`}
                              style={{ width: "75px", maxHeight: "34px", objectFit: "contain" }}
                            />
                          </div>
                  
                          <div style={{ marginTop: '-8px', fontWeight: 'bold', fontSize: '18px' }}>
                            {manufacturerName}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                  
                </ul>
              </div>}
              {recommendations.length > 0 && <div
                className="suggestions-column"
                style={{
                  backgroundColor: "#f2f2f2",
                  borderRadius: "16px",
                  width: "88%",
                  flex: "2",
    
                }}
              >
                <h3>Recommendations</h3>
                <ul>
                  {
                    recommendations.map((rec, index) => (
                        <li
                          key={index}
                          style={{ marginBottom: "10px" }}
                        >
                          <div style={{ display: "flex", alignItems: "center" }}>
                            <div style={{ marginRight: "20px" }}>
                              <img
                                src={rec.imageURL}
                                alt="Recommendation"
                                style={{ width: "80px" }}
                              />
                            </div>
                            <div
                              style={{
                                alignSelf: "flex-start",
                                display: "block",
                                textDecoration: "none",
                                color: "black",
                                fontWeight: "600",
                                fontSize:"15px"
                              }}
                            >
                              <div
                                style={{
                                  fontWeight: "500",
                                  color: "black",
                                  textDecoration: "none",
                                }}
                              >
                                <a
                                  href={rec.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                >
                                  <span
                                    dangerouslySetInnerHTML={{
                                      __html: rec.description.replace(
                                        new RegExp(`(${searchTerm})`, "gi"),
                                        "<strong>$1</strong>"
                                      ),
                                    }}
                                  />
                                </a>
                                <div>PartSelect Part #: PS{rec.InventoryID}</div>
                                <div>Manufacturer Part #: {rec.partNum}</div>
                                <div>Manufactured by: {rec.manufacturer}</div>
                              </div>
                            </div>
                          </div>
                        </li>
                      ))}
                </ul>
              </div>}
            </div>
          )}
          {(searchTerm.match(/how to replace.*element.*/) || searchTerm.match(/how to test.*element.*/)) && 
          <div className="suggestions-dropdown">
             <div
                className="suggestions-column"
                style={{
                  backgroundColor: "#f2f2f2",
                  borderRadius: "16px",
                  width: "88%",
                  flex: "2",
                }}>
                  <h3>InstaAgent Insights</h3>
                  <h4>{searchTerm.charAt(0).toUpperCase() + searchTerm.slice(1)}</h4>
                  <hr></hr>
                  {isLoading===true ? (
                    <div>
                      <div className="bar-container">
                        <div className="bar bar-short"></div>
                        <div className="bar bar-long"></div>
                        <div className="bar bar-medium"></div>
                      </div>
                    </div>
                ): <div dangerouslySetInnerHTML={{ __html: custServResponse }} />}
            </div>
          </div>
          }
        </div>
        // </div>
      );
};