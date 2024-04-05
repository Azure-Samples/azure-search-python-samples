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
        setIsLoading(true);
        setModelSuggestions([]);
        setPartSuggestions([]);
        setManufacturers([]);
        setRecommendations([]);
        setError(null);
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
          <div ref={searchBarRef}>
          <form onSubmit={handleSubmit}>
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
                  right: '11%',
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
            manufacturers.length > 0 ||
            recommendations.length > 0) && (isDropdownVisible) && (
            <div className="suggestions-dropdown">
              {modelSuggestions.length > 0 && <div className="suggestions-column">
                <h3>Matching Models</h3>
                <ul>
                  {
                    modelSuggestions.map((suggestion, index) => (
                        <li
                          key={index}
                          onClick={() => {
                            props.onSearchHandler(suggestion);
                            setSearchTerm("");
                          }}
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
                          onClick={() => {
                            props.onSearchHandler(suggestion);
                            setSearchTerm("");
                          }}
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
                        onClick={() => {
                          console.log("clickled on model")
                          props.onSearchHandler(manufacturerName);
                          setSearchTerm("");
                        }}
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
                  borderRadius: "16px",
                  width: "100%",
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
                                  href={`/search?q=${encodeURIComponent(rec.partNum)}`}
                                  onClick={() => {
                                    console.log(encodeURIComponent(rec.partNum))
                                    setSearchTerm("");
                                  }}
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
          {
            (searchTerm && searchTerm.length>0 && searchTerm.length<3 && searchTerm.length<maxQueryLen) && (modelSuggestions.length === 0 &&
              partSuggestions.length === 0 &&
              manufacturers.length === 0 &&
              recommendations.length === 0) && (!isLoading)
              &&
              (
                <div className="suggestions-dropdown">
                  <div className="suggestions-column" >
                    <h3>Keep typing for more specific results...</h3>
                  </div>
                </div>
              )
          }
          {
            (searchTerm && searchTerm.length>0 && searchTerm.length>3 && searchTerm.length<maxQueryLen) && (modelSuggestions.length === 0 &&
              partSuggestions.length === 0 &&
              manufacturers.length === 0 &&
              recommendations.length === 0) && (!isLoading)
              &&
              (
                <div className="suggestions-dropdown">
                  <div className="suggestions-column" >
                    <h3>No search results found.</h3>
                  </div>
                </div>
              )
          }
        </div>
      );
};